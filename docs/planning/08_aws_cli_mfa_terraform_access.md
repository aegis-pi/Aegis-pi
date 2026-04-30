# AWS CLI MFA 및 Terraform 접근 설정

상태: source of truth
기준일: 2026-04-30

## 목적

M1 Hub 클라우드 구성을 시작하기 전에 로컬 터미널에서 AWS CLI와 Terraform이 동일한 임시 MFA 세션을 사용하도록 준비한다.

이 문서는 이미 IAM 사용자, Access Key, 권한, MFA 장치가 준비되어 있다는 전제를 둔다. 새 IAM 계정 생성이나 권한 부여 절차는 다루지 않는다.

## 현재 적용 상태

2026-04-30 기준 로컬 WSL 환경에서 AWS CLI MFA 및 Terraform 접근 설정을 완료했다.

현재 로컬 적용값:

```text
Tools root: /home/vicbear/Aegis/.tools
AWS CLI: /home/vicbear/Aegis/.tools/bin/aws
Terraform: /home/vicbear/Aegis/.tools/bin/terraform
jq: /home/vicbear/Aegis/.tools/bin/jq
MFA script: /home/vicbear/Aegis/.tools/aws-mfa-script
Shell env loader: /home/vicbear/Aegis/.tools/aegis-aws-env.sh
Default AWS region: ap-south-1
Default AWS output: json
```

`~/.bashrc`에는 다음 환경 로더가 등록되어 있다.

```bash
source /home/vicbear/Aegis/.tools/aegis-aws-env.sh
```

검증 완료 항목:

- `aws configure` 기본 프로필 구성 완료
- MFA device ARN을 `mfa.cfg`에 구성 완료
- `mfa <OTP>` 실행 시 STS 임시 credential 환경 변수 설정 확인
- `aws sts get-caller-identity`로 대상 AWS 계정 연결 확인
- 동일 shell에서 Terraform 실행 준비 완료

보안상 Access Key, Secret Access Key, Session Token, MFA OTP, 실제 MFA ARN 값은 이 문서에 기록하지 않는다.

## 기준 방식

AWS 장기 자격 증명은 로컬 AWS CLI 기본 프로필에 저장하고, 실제 작업은 `aws sts get-session-token` 기반의 임시 세션으로 수행한다.

사용 방식은 다음 흐름을 따른다.

```text
기존 IAM Access Key
    -> aws configure
    -> MFA OTP 입력
    -> STS 임시 세션 발급
    -> 환경 변수 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN 설정
    -> aws cli / terraform 실행
```

Terraform provider에는 별도 장기 credential을 적지 않고, 현재 shell의 AWS 환경 변수를 사용하게 한다.

## 사전 조건

- 기존 IAM 사용자가 준비되어 있어야 한다.
- 해당 IAM 사용자에 AWS CLI Access Key와 Secret Access Key가 발급되어 있어야 한다.
- IAM 사용자에 MFA 장치가 등록되어 있어야 한다.
- MFA 장치 ARN을 알고 있어야 한다.
- 로컬에 `aws`, `terraform`, `git`, `bash`, `jq`가 설치되어 있어야 한다.
- M1에서 필요한 AWS 권한이 이미 부여되어 있어야 한다.

권한이 부족한 경우 이 문서에서 해결하지 않는다. `AccessDenied`가 발생하면 필요한 AWS 서비스와 액션을 기준으로 관리자에게 권한 추가를 요청한다.

## MFA 스크립트 설치 기준

MFA 입력을 줄이기 위해 `aws-mfa-script`를 내려받는다. 일반적인 설치 위치는 홈 디렉터리지만, 현재 Aegis 로컬 환경은 프로젝트 내부 `.tools` 경로를 사용한다.

현재 적용 경로:

```bash
git clone https://github.com/asagage/aws-mfa-script.git /home/vicbear/Aegis/.tools/aws-mfa-script
```

일반 설치 예:

```bash
cd ~
git clone https://github.com/asagage/aws-mfa-script.git
cd aws-mfa-script
```

서드파티 스크립트는 shell에 source되어 credential 환경 변수를 설정하므로, 사용 전에 내용을 확인한다.

```bash
sed -n '1,200p' alias.sh
sed -n '1,240p' mfa.sh
```

설정 파일을 생성한다.

현재 로컬 환경에서는 다음 파일을 수정한다.

```bash
nano /home/vicbear/Aegis/.tools/aws-mfa-script/mfa.cfg
```

`default` 항목에 본인 MFA ARN을 입력한다.

```text
default="arn:aws:iam::<ACCOUNT_ID>:mfa/<USER_NAME>"
```

예시는 형식 확인용이다. 실제 계정 ID, 사용자명, Access Key, Secret Key, Session Token은 문서나 Git에 기록하지 않는다.

## AWS CLI 기본 자격 증명 설정

기존 Access Key와 Secret Access Key를 로컬 기본 프로필에 등록한다.

```bash
aws configure
```

권장 입력값:

```text
AWS Access Key ID: 기존 IAM Access Key
AWS Secret Access Key: 기존 IAM Secret Access Key
Default region name: ap-south-1
Default output format: json
```

Aegis-Pi AWS Hub의 기본 리전은 `ap-south-1`로 둔다.

## bash alias 등록

터미널을 열 때 `aws`, `terraform`, `jq`, `mfa` 명령을 사용할 수 있도록 `.bashrc`에 Aegis 로컬 환경 로더를 source한다.

```bash
nano ~/.bashrc
```

아래 줄을 추가한다.

```bash
source /home/vicbear/Aegis/.tools/aegis-aws-env.sh
```

현재 shell에 반영한다.

```bash
source ~/.bashrc
```

## MFA 세션 발급

휴대폰 또는 인증 앱에 표시되는 6자리 OTP를 넣어 임시 credential을 발급한다.

```bash
mfa 123456
```

`123456`은 예시다. 실제 OTP를 입력한다.

정상 동작하면 현재 shell에 다음 환경 변수가 설정된다.

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
```

확인은 다음 명령으로 한다.

```bash
env | grep '^AWS_'
```

`AWS_PROFILE`이 설정되어 있으면 환경 변수 기반 세션보다 profile 설정이 우선되거나 혼동을 만들 수 있다. Terraform 작업 전에는 기본적으로 unset한다.

```bash
unset AWS_PROFILE
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION=ap-south-1
```

## AWS 연결 검증

현재 shell이 어떤 AWS 주체로 동작하는지 확인한다.

```bash
aws sts get-caller-identity
```

기대 결과:

```text
Account: 대상 AWS 계정 ID
Arn: MFA 세션이 적용된 IAM 사용자 ARN 또는 assumed session ARN
UserId: AWS가 반환한 사용자/세션 식별자
```

AWS 서비스 접근 권한도 최소 하나 이상 확인한다.

```bash
aws s3 ls
aws eks list-clusters
aws iot list-things
```

리소스가 아직 없으면 빈 목록이 나올 수 있다. `AccessDenied`가 아니라면 연결 자체는 정상이다.

## Terraform 사용 기준

Terraform provider에는 Access Key, Secret Key, Session Token을 직접 적지 않는다.

```hcl
provider "aws" {
  region = "ap-south-1"
}
```

동일 shell에서 Terraform을 실행한다.

```bash
terraform init
terraform plan
```

MFA 세션이 만료되면 다시 실행한다.

```bash
mfa 123456
terraform plan
```

## Terraform backend 기준

초기 실험 단계에서는 local backend로 시작할 수 있다. 다만 M1 Hub 인프라를 팀 기준으로 관리하려면 S3 backend와 DynamoDB lock을 쓰는 편이 안전하다.

S3 backend를 사용할 경우 다음 리소스가 필요하다.

```text
Terraform state bucket
DynamoDB lock table
KMS key 선택 사항
```

이미 권한이 있다면 MFA 세션을 발급한 뒤 Terraform으로 backend 리소스를 만들 수 있다. 권한이 없으면 관리자에게 backend용 S3 bucket과 DynamoDB table을 먼저 생성해 달라고 요청한다.

## 보안 기준

- `~/.aws/credentials`, `~/.aws/config`, `/home/vicbear/Aegis/.tools/aws-mfa-script/mfa.cfg`를 Git에 커밋하지 않는다.
- Access Key, Secret Access Key, Session Token, MFA OTP를 문서에 기록하지 않는다.
- 서드파티 shell script는 source하기 전에 내용을 확인한다.
- MFA OTP를 command line argument로 입력하면 shell history에 남을 수 있다. 개인 개발 장비에서만 사용하고, 공유 장비에서는 history 정책을 별도로 확인한다.
- Terraform 코드에는 credential 값을 변수, provider, backend config로 하드코딩하지 않는다.
- M1 작업 중 생성되는 인증서, kubeconfig, IoT Core private key는 별도 보관 기준을 둔다.

## 검증 체크리스트

- [x] `aws configure`에 기존 IAM Access Key가 등록되어 있다.
- [x] `/home/vicbear/Aegis/.tools/aws-mfa-script/mfa.cfg`에 MFA ARN이 등록되어 있다.
- [x] `source /home/vicbear/Aegis/.tools/aegis-aws-env.sh`가 `.bashrc`에 등록되어 있다.
- [x] `mfa <OTP>` 실행 후 `AWS_SESSION_TOKEN`이 설정된다.
- [x] `aws sts get-caller-identity`가 대상 계정을 반환한다.
- [x] `unset AWS_PROFILE` 후 Terraform이 현재 shell의 MFA 세션을 사용한다.
- [x] `terraform init`이 성공한다.
- [x] `terraform plan`에서 인증 오류가 발생하지 않는다.

## 문제 해결

### `mfa: command not found`

`.bashrc`가 현재 shell에 반영되지 않았거나 `alias.sh` 경로가 틀린 상태다.

```bash
source ~/.bashrc
ls /home/vicbear/Aegis/.tools/aws-mfa-script/alias.sh
```

### `AccessDenied`

MFA 인증은 성공했지만 해당 AWS 액션 권한이 부족한 상태다. 실패한 서비스와 액션을 확인해 권한을 추가해야 한다.

```text
예: eks:CreateCluster, iam:CreateRole, s3:CreateBucket, iot:CreateThing
```

### `The security token included in the request is expired`

STS 임시 세션이 만료된 상태다.

```bash
mfa 123456
```

### `InvalidClientTokenId` 또는 `SignatureDoesNotMatch`

장기 Access Key 설정이 틀렸거나, 오래된 환경 변수가 shell에 남아 있을 수 있다.

```bash
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_SESSION_TOKEN
unset AWS_PROFILE
aws configure
source ~/.bashrc
mfa 123456
```

### `jq: command not found`

스크립트가 STS 응답을 파싱하는 데 `jq`를 요구할 수 있다. 운영체제에 맞게 설치한다.

```bash
sudo apt-get update
sudo apt-get install -y jq
```

### Terraform은 실패하지만 AWS CLI는 성공

Terraform을 실행하는 shell과 `mfa`를 실행한 shell이 다른지 확인한다. IDE 터미널, 새 탭, tmux pane마다 환경 변수가 다를 수 있다.

```bash
aws sts get-caller-identity
env | grep '^AWS_'
terraform plan
```

## M1 착수 기준

이 문서의 검증 체크리스트가 완료되면 M1에서 다음 작업을 시작할 수 있다.

- EKS 클러스터 생성
- S3 bucket 및 경로 파티셔닝 구성
- IoT Core Thing, 인증서, IoT Rule 구성
- AMP workspace 구성
- Dashboard VPC 네트워크 및 ALB/Auth 설계
