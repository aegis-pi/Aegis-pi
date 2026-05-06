# IoT Core Thing and K3s Secret Mount Runbook

상태: source of truth
기준일: 2026-05-04

## 수정 버전

| 일자 | 수정 내용 |
| --- | --- |
| 2026-05-04 | 실제 생성된 `factory-a` IoT Thing/Policy/K3s Secret 기준으로 Thing 이름, 저장 위치, 자동화 스크립트, SSH 대상, Secret 이름을 최신화 |

## 목적

`factory-a` Edge Agent가 AWS IoT Core로 MQTT publish할 수 있도록 IoT Core Thing, 인증서, Policy를 만들고, 인증서를 `factory-a` K3s Secret으로 주입하는 절차를 정리한다.

이 문서는 `edge-agent` 구현 전에도 먼저 수행할 수 있는 IoT Core 인증 기반 준비 절차다. `edge-agent`는 Thing 자체가 아니라, Thing에 연결된 인증서를 사용하는 K3s workload다.

## 기준 결정

Thing 등록은 AWS IoT Core에서 공장 단위로 한다.

```text
Thing:
  AEGIS-IoTThing-factory-a
  AEGIS-IoTThing-factory-b
  AEGIS-IoTThing-factory-c
```

`factory-a` MVP에서는 먼저 `AEGIS-IoTThing-factory-a`만 생성했다.

K3s에는 Thing을 등록하지 않는다. K3s에는 해당 Thing에 연결된 인증서와 private key를 Kubernetes Secret으로 주입하고, `edge-agent` Deployment가 그 Secret을 read-only volume으로 mount한다.

```text
AWS IoT Core:
  Thing
  Certificate
  Policy
  Thing <-> Certificate attachment
  Certificate <-> Policy attachment

factory-a K3s:
  namespace: ai-apps
  Secret: aws-iot-factory-a-cert
  ConfigMap: edge-agent-config
  Deployment: edge-agent
```

## 개발 순서

권장 순서는 아래와 같다.

```text
1. IoT Core Thing / Certificate / Policy 생성
2. IoT Core endpoint 확인
3. 현재 PC에 인증서 파일 임시 저장
4. Raspberry Pi master로 인증서 파일 전달
5. master에서 K3s Secret 생성
6. master의 임시 인증서 파일 삭제
7. edge-agent 없이 테스트 publish 또는 MQTT test client로 인증 확인
8. edge-agent 최소 구현 후 Secret mount 연결
9. IoT Core Rule -> S3 적재 연결
```

`edge-agent` 구현을 완료해야만 Thing을 만들 수 있는 것은 아니다. Thing과 인증서는 먼저 만들고, `edge-agent`는 이후 그 인증서를 사용하도록 붙인다.

## 파일 보관 원칙

인증서와 private key는 Git repository에 넣지 않는다.

현재 PC에서는 repository 내부의 Git 제외 디렉터리인 `secret/`만 사용한다.

```text
secret/iot/factory-a/
  certificate.pem.crt
  private.pem.key
  AmazonRootCA1.pem
  endpoint.txt
  registration-summary.txt
```

로컬 보관 디렉터리는 백업, 공유, 커밋 대상이 아니다. 운영 전에는 별도 Secret 관리 방식을 다시 정한다.

```text
MVP:
  kubectl create secret 수동 주입

후속 운영 후보:
  SealedSecrets
  External Secrets Operator
  SOPS
```

## IoT Core 리소스 생성

AWS CLI는 MFA 임시 세션이 활성화된 shell에서 실행한다.

```bash
source ~/.bashrc
mfa <OTP>
unset AWS_PROFILE
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION=ap-south-1
aws sts get-caller-identity
```

Thing을 생성한다.

```bash
scripts/iot/register-thing.sh
```

위 스크립트는 Thing, Policy, certificate/key, Root CA, endpoint를 생성해 `secret/iot/factory-a/`에 저장한다.

수동으로 생성해야 할 때 Thing 이름은 아래 기준을 따른다.

```bash
aws iot create-thing \
  --thing-name AEGIS-IoTThing-factory-a
```

인증서를 수동 생성하고 파일로 저장한다.

```bash
mkdir -p secret/iot/factory-a
cd secret/iot/factory-a

aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile certificate.pem.crt \
  --public-key-outfile public.pem.key \
  --private-key-outfile private.pem.key \
  > certificate-result.json
```

Root CA를 저장한다.

```bash
curl -fsSL https://www.amazontrust.com/repository/AmazonRootCA1.pem \
  -o AmazonRootCA1.pem
```

Certificate ARN을 확인한다.

```bash
jq -r '.certificateArn' certificate-result.json
```

IoT Core endpoint를 확인한다.

```bash
aws iot describe-endpoint \
  --endpoint-type iot:Data-ATS
```

## IoT Policy

`factory-a` Thing은 자기 client id와 자기 topic prefix만 사용한다.

권장 topic prefix:

```text
aegis/factory-a
```

정책 파일 예시:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:ap-south-1:<account-id>:client/AEGIS-IoTThing-factory-a"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": [
        "arn:aws:iot:ap-south-1:<account-id>:topic/aegis/factory-a/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iot:Subscribe",
      "Resource": [
        "arn:aws:iot:ap-south-1:<account-id>:topicfilter/aegis/factory-a/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iot:Receive",
      "Resource": [
        "arn:aws:iot:ap-south-1:<account-id>:topic/aegis/factory-a/*"
      ]
    }
  ]
}
```

정책을 생성한다.

```bash
aws iot create-policy \
  --policy-name AEGIS-IoTPolicy-factory-a \
  --policy-document file://factory-a-iot-policy.json
```

Thing에 인증서를 연결한다.

```bash
CERT_ARN="$(jq -r '.certificateArn' certificate-result.json)"

aws iot attach-thing-principal \
  --thing-name AEGIS-IoTThing-factory-a \
  --principal "$CERT_ARN"
```

인증서에 Policy를 연결한다.

```bash
aws iot attach-policy \
  --policy-name AEGIS-IoTPolicy-factory-a \
  --target "$CERT_ARN"
```

## K3s Secret 주입

현재 PC에서 Raspberry Pi master로 인증서 파일을 전달한다.

```bash
scripts/iot/register-k3s-secret.sh
```

수동으로 수행해야 할 때만 아래 명령을 사용한다.

```bash
ssh minsoo@10.10.10.10 'mkdir -p /tmp/aegis-iot'

scp secret/iot/factory-a/certificate.pem.crt \
    secret/iot/factory-a/private.pem.key \
    secret/iot/factory-a/AmazonRootCA1.pem \
    secret/iot/factory-a/endpoint.txt \
    minsoo@10.10.10.10:/tmp/aegis-iot/
```

master에서 Secret을 생성한다.

```bash
ssh minsoo@10.10.10.10

kubectl get namespace ai-apps >/dev/null 2>&1 || kubectl create namespace ai-apps

kubectl -n ai-apps create secret generic aws-iot-factory-a-cert \
  --from-file=certificate.pem.crt=/tmp/aegis-iot/certificate.pem.crt \
  --from-file=private.pem.key=/tmp/aegis-iot/private.pem.key \
  --from-file=AmazonRootCA1.pem=/tmp/aegis-iot/AmazonRootCA1.pem \
  --from-file=endpoint.txt=/tmp/aegis-iot/endpoint.txt
```

이미 Secret이 있으면 갱신용 manifest를 만들어 적용한다.

```bash
kubectl -n ai-apps create secret generic aws-iot-factory-a-cert \
  --from-file=certificate.pem.crt=/tmp/aegis-iot/certificate.pem.crt \
  --from-file=private.pem.key=/tmp/aegis-iot/private.pem.key \
  --from-file=AmazonRootCA1.pem=/tmp/aegis-iot/AmazonRootCA1.pem \
  --from-file=endpoint.txt=/tmp/aegis-iot/endpoint.txt \
  --dry-run=client -o yaml | kubectl apply -f -
```

Secret 생성 후 master의 임시 파일은 삭제한다.

```bash
rm -rf /tmp/aegis-iot
```

Secret만 확인한다. Secret 값을 출력하지 않는다.

```bash
kubectl -n ai-apps get secret aws-iot-factory-a-cert
kubectl -n ai-apps describe secret aws-iot-factory-a-cert
```

## edge-agent Mount 기준

`edge-agent` Deployment는 인증서 Secret을 `/etc/aegis/iot`에 read-only로 mount한다.

```yaml
volumeMounts:
  - name: aws-iot-cert
    mountPath: /etc/aegis/iot
    readOnly: true

volumes:
  - name: aws-iot-cert
    secret:
      secretName: aws-iot-factory-a-cert
```

컨테이너 내부 파일 경로는 아래처럼 고정한다.

```text
/etc/aegis/iot/certificate.pem.crt
/etc/aegis/iot/private.pem.key
/etc/aegis/iot/AmazonRootCA1.pem
```

환경변수 기준:

```yaml
env:
  - name: AWS_IOT_CLIENT_ID
    value: AEGIS-IoTThing-factory-a
  - name: FACTORY_ID
    value: factory-a
  - name: AWS_IOT_TOPIC_PREFIX
    value: aegis/factory-a
  - name: ENVIRONMENT_TYPE
    value: physical-rpi
  - name: INPUT_MODULE_TYPE
    value: sensor
  - name: EDGE_AGENT_MODE
    value: real
  - name: EDGE_AGENT_QOS
    value: "1"
  - name: AWS_IOT_CERT_PATH
    value: /etc/aegis/iot/certificate.pem.crt
  - name: AWS_IOT_PRIVATE_KEY_PATH
    value: /etc/aegis/iot/private.pem.key
  - name: AWS_IOT_ROOT_CA_PATH
    value: /etc/aegis/iot/AmazonRootCA1.pem
```

## 검증 기준

IoT Core 콘솔의 MQTT 테스트 클라이언트에서 아래 topic을 구독한다.

```text
aegis/factory-a/#
```

초기 연결 검증은 `edge-agent` 구현 전이라도 임시 MQTT client로 수행할 수 있다. 다만 임시 client도 동일한 인증서, client id, topic prefix를 사용해야 한다.

정상 기준:

```text
Thing: AEGIS-IoTThing-factory-a
Certificate: ACTIVE
Policy: AEGIS-IoTPolicy-factory-a attached
Thing principal: certificate attached
K3s Secret: ai-apps/aws-iot-factory-a-cert exists
edge-agent mount path: /etc/aegis/iot
MQTT client id: AEGIS-IoTThing-factory-a
Topic prefix: aegis/factory-a
```

## 보안 주의

- `private.pem.key`는 Git repository, 문서, evidence, Slack, 이메일에 올리지 않는다.
- `kubectl get secret -o yaml` 결과는 base64 인코딩된 secret 값을 포함하므로 문서에 붙이지 않는다.
- `scp`로 master에 전달한 `/tmp/aegis-iot` 파일은 Secret 생성 후 즉시 삭제한다.
- 인증서 교체 시 기존 certificate를 IoT Core에서 비활성화하거나 삭제하는 절차를 별도로 기록한다.
- 운영 단계에서는 수동 Secret 주입 대신 SealedSecrets, External Secrets Operator, SOPS 중 하나로 전환한다.

## 관련 문서

- `docs/planning/06_edge_agent_deployment_plan.md`
- `docs/issues/M1_hub-cloud.md`
- `docs/issues/M4_data-plane.md`
- `docs/ops/10_edge_workload_placement.md`
- `docs/planning/08_aws_cli_mfa_terraform_access.md`
