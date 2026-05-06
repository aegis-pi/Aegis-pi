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
| `register-k3s-secret.sh` | 로컬 인증서 파일을 K3s master로 전송한 뒤 Kubernetes Secret 생성/갱신 |
| `publish-test-message.sh` | IoT Rule -> S3 적재 검증용 테스트 메시지 publish |
| `cleanup-thing.sh` | CLI로 만든 IoT Thing, Policy, certificate 정리 |

## 기본 출력 위치

```text
secret/iot/factory-a/
```

이 경로는 `.gitignore`의 `secret/` 규칙으로 Git에서 제외된다.

## 등록 실행

MFA session이 없으면 실행 초기에 OTP를 입력받는다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/iot/register-thing.sh
```

OTP를 인자로 넘길 수도 있다.

```bash
scripts/iot/register-thing.sh <MFA_OTP>
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

## K3s Secret 등록 자동화

기본 대상은 `factory-a` master `10.10.10.10`이다. SSH 비밀번호는 저장하지 않고 `ssh`/`scp`가 직접 입력받는다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/iot/register-k3s-secret.sh
```

기본값:

```text
FACTORY_ID=factory-a
SECRET_DIR=secret/iot/factory-a
REMOTE_USER=minsoo
REMOTE_HOST=10.10.10.10
REMOTE_DIR=/tmp/aegis-iot-factory-a
K8S_NAMESPACE=ai-apps
K8S_SECRET_NAME=aws-iot-factory-a-cert
```

다른 SSH 사용자로 접속해야 하면:

```bash
REMOTE_USER=<ssh-user> scripts/iot/register-k3s-secret.sh
```

스크립트가 수행하는 작업:

```text
1. local secret 파일 존재 확인
2. scp로 master /tmp 디렉터리에 임시 복사
3. ai-apps namespace 생성/갱신
4. aws-iot-factory-a-cert Secret 생성/갱신
5. master의 임시 인증서 파일 삭제
6. Secret 존재 확인
```

## K3s Secret 수동 등록

자동화 스크립트를 쓰지 않을 때만 아래 명령을 사용한다.

```bash
SECRET_DIR=/home/vicbear/Aegis/git_clone/Aegis-pi/secret/iot/factory-a

kubectl get namespace ai-apps >/dev/null 2>&1 || kubectl create namespace ai-apps

kubectl -n ai-apps create secret generic aws-iot-factory-a-cert \
  --from-file=certificate.pem.crt="${SECRET_DIR}/certificate.pem.crt" \
  --from-file=private.pem.key="${SECRET_DIR}/private.pem.key" \
  --from-file=AmazonRootCA1.pem="${SECRET_DIR}/AmazonRootCA1.pem" \
  --from-file=endpoint.txt="${SECRET_DIR}/endpoint.txt" \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 테스트 메시지 발행

IoT Rule이 생성된 뒤 S3 적재를 검증할 때 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/iot/publish-test-message.sh
```

기본 publish 대상:

```text
topic: aegis/factory-a/sensor
expected S3 prefix: s3://aegis-bucket-data/raw/factory-a/sensor/
```

다른 source type으로 보낼 때:

```bash
SOURCE_TYPE=system scripts/iot/publish-test-message.sh
```

## 정리 실행

AWS IoT 리소스만 정리하고 local secret 파일은 보존한다.

```bash
scripts/iot/cleanup-thing.sh
```

OTP를 인자로 넘길 수도 있다.

```bash
scripts/iot/cleanup-thing.sh <MFA_OTP>
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
kubectl -n ai-apps delete secret aws-iot-factory-a-cert
```

## 주의

- `private.pem.key`는 절대 Git에 넣지 않는다.
- `certificate.json`도 Git에 넣지 않는다.
- 실제 출력물은 `secret/` 아래에만 둔다.
- 장기 운영에서는 Ansible 또는 외부 Secret 관리 도구로 교체할 수 있다.
