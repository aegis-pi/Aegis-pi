# Hub Scripts

상태: source of truth
기준일: 2026-06-04

## 목적

이 디렉터리는 기존 `scripts/hub/*` 경로를 보존하기 위한 호환 wrapper 스크립트를 둔다. 실제 생성/삭제/운영 진입점은 `scripts/build/`, `scripts/destroy/`, `scripts/ops/`가 기준이다.

책임 경계는 `docs/planning/11_delivery_ownership_flow.md`를 따른다.

```text
Terraform: AWS 인프라 생성/삭제
Ansible: EKS 위 namespace, LimitRange, ArgoCD/Grafana/Tailscale 설치 및 검증
scripts/build: 생성 진입점
scripts/ops: 운영 진입점
scripts/destroy: 삭제 진입점
scripts/hub: 기존 경로 호환 wrapper
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
| `run-hub.sh` | `scripts/build/build-hub.sh` 실행 후 ArgoCD port-forward 실행 | AWS 리소스 생성 |
| `destroy-hub.sh` | `scripts/destroy/destroy-hub.sh` 호출 | AWS 리소스 삭제 |
| `argocd-port-forward.sh` | `scripts/ops/argocd-port-forward.sh` 호출 | 리소스 변경 없음 |
| `argocd-initial-password.sh` | `scripts/ops/argocd-initial-password.sh` 호출 | 리소스 변경 없음 |

## `run-hub.sh`

Hub를 처음 올리거나 destroy 이후 다시 만들 때 사용한다.

권장 실행 경로는 `scripts/build/build-hub.sh`다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
```

OTP를 인자로 넘길 수도 있다.

```bash
scripts/build/build-hub.sh <MFA_OTP>
```

현재 `build-hub.sh` 실행 순서:

```text
1. MFA OTP 입력
2. AWS MFA session 설정
3. infra/hub terraform init
4. infra/hub terraform validate
5. infra/hub terraform plan -out=tfplan
6. infra/hub terraform apply tfplan
7. 유지 중인 SlowCollector IAM role이 있으면 data-pipeline EKS access entry/view policy 자동 복구
8. scripts/ansible Hub platform bootstrap/verify 실행
   - ArgoCD
   - legacy Prometheus Agent cleanup
   - Grafana
   - AWS Load Balancer Controller
9. secret/hub-ui-credentials.txt 갱신
```

SlowCollector IAM role이 존재하지만 data-pipeline Terraform state를 remote backend에서 읽을 수 없거나 state가 비어 있으면 안전한 target apply를 보장할 수 없어 중단한다. 명시적으로 건너뛰려면 `RECONCILE_DATA_PIPE_EKS_ACCESS=false`를 사용한다.

ArgoCD Helm release가 이미 `deployed` 상태이고 chart version이 같으면 bootstrap playbook은 Helm upgrade를 건너뛴다. 강제 재적용은 아래처럼 실행한다.

```bash
FORCE_ARGOCD_UPGRADE=true scripts/build/build-hub.sh
```

Tailscale Operator, Spoke egress, ArgoCD/Grafana Tailnet UI, ArgoCD cluster Secret, ApplicationSet은 `build-hub.sh` 기본 흐름에서 실행하지 않는다. 필요 시 `scripts/build/connect-hub-tailscale-ui.sh` 또는 `scripts/build/register-spoke-factory-a.sh`, `register-spoke-factory-b.sh`, `register-spoke-factory-c.sh`를 별도로 실행한다.

Hub-only 데이터 수집 유지 재시작에서는 factory별 등록 스크립트에 `HUB_ONLY_RECONNECT=true`를 사용한다. 이 모드에서는 data-pipeline, ECS backend, factory-b/c dummy generator와 Spoke publisher를 재생성하거나 재시작하지 않는다.

`scripts/hub/run-hub.sh` wrapper를 사용하면 build 이후 port-forward까지 이어서 foreground로 실행된다. 중지하려면 `Ctrl+C`를 사용한다.

## `destroy-hub.sh`

Hub 실험을 끝내고 비용이 발생하는 AWS 리소스를 제거할 때 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/destroy/destroy-hub.sh
```

OTP를 인자로 넘길 수도 있다.

```bash
scripts/destroy/destroy-hub.sh <MFA_OTP>
```

실행 순서:

```text
1. MFA OTP 입력
2. AWS MFA session 설정
3. infra/hub terraform init
4. infra/hub terraform validate
5. infra/hub terraform destroy
```

`destroy-hub.sh`는 EKS, node group, NAT Gateway 등 `infra/hub` Terraform state가 관리하는 리소스를 제거한다. ArgoCD, namespace, Tailscale Operator/proxy Service는 EKS 내부 리소스이므로 EKS destroy와 함께 제거된다. `factory-a-master` Tailscale device와 OAuth client는 삭제하지 않는다.

Hub-only 데이터 수집 유지 모드에서는 `destroy-hub.sh`만 실행한다. data-pipeline을 유지하면 다음 `build-hub.sh`가 SlowCollector EKS access binding을 새 Hub에 자동 복구한다.

전체 삭제는 `scripts/destroy/destroy-all.sh`를 사용한다. 기본값은 reporting/data-pipeline/Hub 삭제이며 IoT와 foundation은 보존한다. `DESTROY_IOT=true`, `DESTROY_FOUNDATION=true`를 명시한 경우에만 IoT Thing/certificate/K3s Secret과 foundation 영속 리소스까지 삭제한다.

## `argocd-port-forward.sh`

이미 Hub EKS와 ArgoCD가 올라와 있을 때 UI만 로컬에서 열기 위해 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/ops/argocd-port-forward.sh
```

접속 주소:

```text
https://127.0.0.1:8080
```

초기 admin 비밀번호도 같이 출력하려면 아래처럼 실행한다.

```bash
scripts/ops/argocd-port-forward.sh --print-password
```

환경 변수로 기본값을 바꿀 수 있다.

```bash
AWS_REGION=ap-south-1 \
CLUSTER_NAME=AEGIS-EKS \
ARGOCD_NAMESPACE=argocd \
ARGOCD_LOCAL_PORT=8080 \
scripts/ops/argocd-port-forward.sh
```

## `argocd-initial-password.sh`

ArgoCD 초기 admin 비밀번호만 조회할 때 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/ops/argocd-initial-password.sh
```

현재 shell에 `AWS_SESSION_TOKEN`이 없으면 MFA OTP를 먼저 입력받는다.

OTP를 인자로 넘길 수도 있다.

```bash
scripts/ops/argocd-initial-password.sh <MFA_OTP>
```

환경 변수로 기본값을 바꿀 수 있다.

```bash
AWS_REGION=ap-south-1 \
CLUSTER_NAME=AEGIS-EKS \
ARGOCD_NAMESPACE=argocd \
scripts/ops/argocd-initial-password.sh
```

## 권장 사용 순서

Hub를 새로 만들고 UI에 들어갈 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
```

다른 터미널에서 초기 비밀번호를 확인할 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/ops/argocd-initial-password.sh
```

작업이 끝나 Hub를 제거할 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/destroy/destroy-hub.sh
```

## 주의

- `run-hub.sh`는 AWS 리소스를 만든다.
- `destroy-hub.sh`는 AWS 리소스를 삭제한다.
- 장시간 사용하지 않을 때는 `destroy-hub.sh`로 제거한다.
- ArgoCD public `LoadBalancer`는 만들지 않는다.
- UI 접근은 필요에 따라 kubeconfig 기반 `kubectl port-forward`, Admin UI HTTPS Ingress, 또는 Tailscale UI Service를 선택한다.
