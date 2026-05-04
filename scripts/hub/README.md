# Hub Scripts

상태: source of truth
기준일: 2026-05-04

## 목적

이 디렉터리는 Hub EKS 실험 환경을 로컬에서 올리고, ArgoCD bootstrap 이후 UI에 접근하고, 실험 종료 시 제거하기 위한 실행 스크립트를 둔다.

책임 경계는 `docs/planning/11_delivery_ownership_flow.md`를 따른다.

```text
Terraform: AWS 인프라 생성/삭제
Ansible: EKS 위 namespace, LimitRange, ArgoCD 설치 및 검증
Hub scripts: 위 절차를 로컬에서 순서대로 실행하는 wrapper
```

## 전제 조건

- 로컬 AWS CLI MFA helper가 준비되어 있어야 한다.
- 기본 리전은 `ap-south-1`이다.
- 대상 EKS cluster 이름은 `AEGIS-EKS`다.
- `terraform`, `aws`, `kubectl`, `helm`, `ansible-playbook` 명령을 로컬에서 실행할 수 있어야 한다.
- 비밀번호, MFA OTP, AWS session token은 문서나 Git에 저장하지 않는다.

## 실행 파일

| 파일 | 목적 | 리소스 영향 |
| --- | --- | --- |
| `run-hub.sh` | MFA OTP 입력 후 Hub 인프라 생성, Ansible bootstrap, ArgoCD 검증, port-forward 실행 | AWS 리소스 생성 |
| `destroy-hub.sh` | MFA OTP 입력 후 Hub 인프라 제거 | AWS 리소스 삭제 |
| `argocd-port-forward.sh` | 기존 Hub EKS의 ArgoCD UI를 로컬 `https://127.0.0.1:8080`으로 연결 | 리소스 변경 없음 |
| `argocd-initial-password.sh` | ArgoCD 초기 admin 비밀번호 조회 | 리소스 변경 없음 |

## `run-hub.sh`

Hub를 처음 올리거나 destroy 이후 다시 만들 때 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/hub/run-hub.sh
```

OTP를 인자로 넘길 수도 있다.

```bash
scripts/hub/run-hub.sh <MFA_OTP>
```

실행 순서:

```text
1. MFA OTP 입력
2. AWS MFA session 설정
3. infra/hub terraform init
4. infra/hub terraform validate
5. infra/hub terraform plan -out=tfplan
6. infra/hub terraform apply tfplan
7. scripts/ansible hub_argocd_bootstrap.yml 실행
8. scripts/ansible hub_argocd_verify.yml 실행
9. argocd-port-forward.sh 실행
```

마지막 단계의 port-forward는 foreground에서 계속 실행된다. 중지하려면 `Ctrl+C`를 사용한다.

## `destroy-hub.sh`

Hub 실험을 끝내고 비용이 발생하는 AWS 리소스를 제거할 때 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/hub/destroy-hub.sh
```

OTP를 인자로 넘길 수도 있다.

```bash
scripts/hub/destroy-hub.sh <MFA_OTP>
```

실행 순서:

```text
1. MFA OTP 입력
2. AWS MFA session 설정
3. infra/hub terraform init
4. infra/hub terraform validate
5. infra/hub terraform destroy
```

`destroy-hub.sh`는 EKS, node group, NAT Gateway 등 `infra/hub` Terraform state가 관리하는 리소스를 제거한다. ArgoCD와 namespace는 EKS 내부 리소스이므로 EKS destroy와 함께 제거된다.

## `argocd-port-forward.sh`

이미 Hub EKS와 ArgoCD가 올라와 있을 때 UI만 로컬에서 열기 위해 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/hub/argocd-port-forward.sh
```

접속 주소:

```text
https://127.0.0.1:8080
```

초기 admin 비밀번호도 같이 출력하려면 아래처럼 실행한다.

```bash
scripts/hub/argocd-port-forward.sh --print-password
```

환경 변수로 기본값을 바꿀 수 있다.

```bash
AWS_REGION=ap-south-1 \
CLUSTER_NAME=AEGIS-EKS \
ARGOCD_NAMESPACE=argocd \
ARGOCD_LOCAL_PORT=8080 \
scripts/hub/argocd-port-forward.sh
```

## `argocd-initial-password.sh`

ArgoCD 초기 admin 비밀번호만 조회할 때 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/hub/argocd-initial-password.sh
```

현재 shell에 `AWS_SESSION_TOKEN`이 없으면 MFA OTP를 먼저 입력받는다.

OTP를 인자로 넘길 수도 있다.

```bash
scripts/hub/argocd-initial-password.sh <MFA_OTP>
```

환경 변수로 기본값을 바꿀 수 있다.

```bash
AWS_REGION=ap-south-1 \
CLUSTER_NAME=AEGIS-EKS \
ARGOCD_NAMESPACE=argocd \
scripts/hub/argocd-initial-password.sh
```

## 권장 사용 순서

Hub를 새로 만들고 UI에 들어갈 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/hub/run-hub.sh
```

다른 터미널에서 초기 비밀번호를 확인할 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/hub/argocd-initial-password.sh
```

작업이 끝나 Hub를 제거할 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/hub/destroy-hub.sh
```

## 주의

- `run-hub.sh`는 AWS 리소스를 만든다.
- `destroy-hub.sh`는 AWS 리소스를 삭제한다.
- 장시간 사용하지 않을 때는 `destroy-hub.sh`로 제거한다.
- ArgoCD public `LoadBalancer`는 만들지 않는다.
- 현재 UI 접근은 kubeconfig 기반 `kubectl port-forward`를 사용한다.
