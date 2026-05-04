# IoT Scripts

상태: source of truth
기준일: 2026-05-04

## 목적

이 디렉터리는 AWS IoT Core Thing 등록과 인증서 발급을 자동화하는 템플릿 스크립트를 둔다.

스크립트는 Git에 커밋한다. 실제 인증서, private key, certificate ARN, endpoint 같은 출력물은 `secret/` 아래에만 저장한다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `register-thing.sh` | IoT Thing, Policy, certificate/key, Root CA, endpoint 생성 |
| `cleanup-thing.sh` | CLI로 만든 IoT Thing, Policy, certificate 정리 |

## 기본 출력 위치

```text
secret/iot/factory-a/
```

이 경로는 `.gitignore`의 `secret/` 규칙으로 Git에서 제외된다.

## 등록 실행

MFA session이 설정된 shell에서 실행한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/iot/register-thing.sh
```

기본값:

```text
AWS_REGION=ap-south-1
FACTORY_ID=factory-a
THING_NAME=AEGIS-IoTThing-factory-a
POLICY_NAME=AEGIS-IoTPolicy-factory-a
TOPIC_PREFIX=aegis/factory-a
SECRET_DIR=secret/iot/factory-a
```

다른 공장에 사용할 때:

```bash
FACTORY_ID=factory-b scripts/iot/register-thing.sh
```

## 생성되는 local secret 파일

```text
AmazonRootCA1.pem
certificate.json
certificate-arn.txt
certificate-id.txt
certificate.pem.crt
endpoint.txt
iot-policy.json
private.pem.key
public.pem.key
registration-summary.txt
```

## K3s Secret 등록

```bash
SECRET_DIR=/home/vicbear/Aegis/git_clone/Aegis-pi/secret/iot/factory-a

kubectl create namespace edge-system

kubectl -n edge-system create secret generic factory-a-iot-cert \
  --from-file=certificate.pem.crt="${SECRET_DIR}/certificate.pem.crt" \
  --from-file=private.pem.key="${SECRET_DIR}/private.pem.key" \
  --from-file=AmazonRootCA1.pem="${SECRET_DIR}/AmazonRootCA1.pem" \
  --from-file=endpoint.txt="${SECRET_DIR}/endpoint.txt"
```

이미 Secret이 있으면 먼저 삭제하거나 `kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -` 방식으로 갱신한다.

## 정리 실행

AWS IoT 리소스만 정리하고 local secret 파일은 보존한다.

```bash
scripts/iot/cleanup-thing.sh
```

local secret 파일까지 지우려면 명시적으로 설정한다.

```bash
DELETE_LOCAL_FILES=true scripts/iot/cleanup-thing.sh
```

## Terraform destroy와의 관계

이 스크립트로 만든 IoT Thing, Policy, Certificate는 Terraform state에 없다. 따라서 `terraform destroy`로 삭제되지 않는다.

삭제는 `cleanup-thing.sh`로 수행한다.

K3s Secret도 Terraform state에 없다. 필요하면 아래처럼 삭제한다.

```bash
kubectl -n edge-system delete secret factory-a-iot-cert
```

## 주의

- `private.pem.key`는 절대 Git에 넣지 않는다.
- `certificate.json`도 Git에 넣지 않는다.
- 실제 출력물은 `secret/` 아래에만 둔다.
- 장기 운영에서는 Ansible 또는 외부 Secret 관리 도구로 교체할 수 있다.
