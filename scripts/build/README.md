# Build Scripts

상태: source of truth
기준일: 2026-05-20

## 목적

이 디렉터리는 Aegis-Pi 리소스 생성 진입점을 순서대로 관리한다.

새 리소스를 추가하거나 기존 리소스 생성 방식이 바뀌면 이 디렉터리의 스크립트와 문서를 함께 업데이트한다.

## 레이어 구분

리소스를 생애주기 기준으로 4개 레이어로 나눈다.

```text
Layer 0 │ Foundation   │ S3, AMP, ECR, IoT Rule, GitHub Actions OIDC
        │              │ 영구 리소스. 최초 1회 생성 후 일반 빌드 흐름에서 제외.

Layer 1 │ Hub Infra    │ VPC, NAT GW, EKS 클러스터, IRSA Role, Route53, ACM
        │ (Terraform)  │ 비용 주요 발생원. 개발 중단 시 삭제, 재개 시 재생성.

Layer 2 │ Hub Platform │ ArgoCD, Prometheus Agent, Grafana, AWS LB Controller,
        │ (Ansible)    │ Hub 내부 K8s 워크로드.
        │              │ Layer 1 위에 올라가는 K8s 워크로드.

Layer 3 │ IoT          │ IoT Thing/Policy/Certificate, K3s Secret
        │              │ Hub-Spoke Tailscale/ArgoCD cluster Secret,
        │              │ Spoke ApplicationSet 배포. 대상 factory K3s가 켜진 뒤 실행.
```

## 생성 순서

```text
0. foundation (최초 1회만)
   - infra/foundation Terraform apply
   - S3 data bucket, AMP Workspace, ECR, IoT Rule, GitHub Actions OIDC

1. hub-infra
   - infra/hub Terraform apply
   - VPC, subnet, NAT Gateway, EKS 클러스터, node group
   - IRSA Role (LB Controller / Grafana / Prometheus / Risk Normalizer)
   - Route53 Hosted Zone, ACM certificate

2. hub-platform
   - Ansible Hub bootstrap (EKS 위 K8s 워크로드)
   - ArgoCD install/verify
   - Prometheus Agent install/verify and AMP remote_write
   - internal Grafana install/verify and AMP datasource query
   - local secret/hub-ui-credentials.txt 출력
   - AWS Load Balancer Controller install/verify

3. admin-ui-after-ns
   - Gabia NS 위임 확인
   - ACM ISSUED 대기
   - Admin UI HTTPS Ingress bootstrap/verify

4. iot / spoke registration
   - IoT Thing / Policy / certificate 등록
   - local secret/iot/<factory-id> 출력
   - 대상 factory K3s Secret 등록
   - Hub-only rebuild에서는 기존 IoT Secret을 유지하고 UI, factory별 cluster 등록, GitOps ApplicationSet을 별도 실행
```

`build-all.sh`는 1 → 2 → 3 순서로 실행한다. 0(Foundation)은 기본값에서 제외되며 별도 실행한다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `build-all.sh` | 기본 hub-infra → hub-platform 실행. `--foundation`, `--admin-ui-after-ns`, `--iot`로 4단계 선택 실행. |
| `build-admin-ui-after-ns.sh` | Gabia NS 위임 후 ACM 발급을 기다리고 Admin UI HTTPS Ingress 활성화 |
| `build-foundation.sh` | `infra/foundation` Terraform apply. 최초 1회 단독 실행. |
| `build-hub-infra.sh` | `infra/hub` Terraform apply (VPC, EKS, IRSA, Route53, ACM) |
| `build-hub-platform.sh` | Ansible bootstrap (ArgoCD, Prometheus, Grafana, LB Controller) |
| `build-hub.sh` | `build-hub-infra.sh` → `build-hub-platform.sh` 순서 실행 wrapper |
| `build-iot-factory-a.sh` | `factory-a` IoT Thing/certificate, K3s Secret, Hub-Spoke Tailscale, ArgoCD cluster Secret, ApplicationSet 등록 |
| `connect-hub-tailscale-ui.sh` | Hub ArgoCD/Grafana Tailscale UI Service만 연결/검증. Spoke cluster Secret은 등록하지 않음 |
| `register-spoke-factory-a.sh` | 기존 `factory-a` K3s/IoT Secret을 유지하고 Hub ArgoCD cluster Secret과 Spoke Application sync 복구 |
| `register-spoke-factory-b.sh` | 기존 `factory-b` K3s/IoT Secret을 유지하고 Hub ArgoCD cluster Secret과 Spoke Application sync 복구 |
| `register-spoke-factory-c.sh` | 기존 `factory-c` K3s/IoT Secret을 유지하고 Hub ArgoCD cluster Secret과 Spoke Application sync 복구 |

Hub build는 ArgoCD/Grafana 설치 검증 후 `secret/hub-ui-credentials.txt`를 갱신한다. 이 파일은 `.gitignore`의 `secret/` 규칙으로 Git에 들어가지 않으며, 파일 권한은 `0600`으로 설정된다.

## Foundation 생성 (최초 1회)

Foundation은 영구 리소스이므로 최초 1회만 실행한다. `build-all.sh`의 기본 흐름에 포함되지 않는다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-foundation.sh [MFA_OTP]
```

## 일반 개발 사이클 (Hub)

Foundation이 이미 존재하는 상태에서 Hub를 올린다. Hub Terraform은 이 단계에서 Route53 Hosted Zone, ACM Certificate, ACM validation record를 만들고 `secret/admin-ui-nameservers.txt`를 갱신한다. Admin UI Ingress/ALB는 기본 생성하지 않는다.

```bash
scripts/build/build-all.sh [MFA_OTP]
```

`build-all.sh`의 기본 동작:

```text
BUILD_FOUNDATION=false  ← Foundation은 기본 제외
BUILD_HUB=true          ← hub-infra → hub-platform 순서 실행
BUILD_ADMIN_UI_AFTER_NS=false
BUILD_IOT=false
```

Foundation까지 포함해 최초 생성하려면 `--foundation`을 붙인다. 이 경우 Foundation을 먼저 생성한 뒤 Hub preflight와 Hub build를 실행한다.

```bash
scripts/build/build-all.sh --foundation [MFA_OTP]
```

Gabia NS 위임이 끝난 뒤 Admin UI HTTPS Ingress까지 함께 올리려면 `--admin-ui-after-ns`를 사용한다.

```bash
scripts/build/build-all.sh --admin-ui-after-ns [MFA_OTP]
```

IoT Thing/certificate와 K3s Secret 등록까지 포함하려면 `--iot`를 사용한다.

```bash
scripts/build/build-all.sh --iot [MFA_OTP]
```

`build-all.sh`는 실제 생성 전에 preflight를 실행한다. preflight는 로컬 CLI, AWS 인증, Hub가 참조하는 foundation state, 기존 Hub Terraform state의 대표 AWS 리소스 조회 가능 여부를 먼저 확인한다. `--iot`가 포함되면 Tailscale secret/kubeconfig도 함께 확인한다.

일시적으로 preflight만 건너뛰려면 아래처럼 실행한다. 디버깅 때만 사용한다.

```bash
AEGIS_BUILD_PREFLIGHT=false scripts/build/build-all.sh
```

AWS state 조회만 건너뛰고 나머지 preflight는 유지하려면:

```bash
AEGIS_PREFLIGHT_AWS_STATE=false scripts/build/build-all.sh
```

## Hub 재개 (개발 재시작)

`stop-dummy-generators.sh`로 VM 데이터 생성을 멈추고 `destroy-all.sh` 또는 `destroy-hub.sh`로 Hub를 내린 뒤 개발을 재개할 때의 절차다.
Foundation은 살아있으므로 Foundation 생성은 건너뛴다.

### 케이스 1 — Hub만 내렸다가 올릴 때 (IoT 유지)

`destroy-hub.sh`를 사용한 경우. IoT Thing/Certificate와 K3s Secret은 그대로 남아있다.

```bash
scripts/build/build-hub.sh [MFA_OTP]
```

Admin UI HTTPS가 필요하면 Hub 생성 직후 출력된 NS를 Gabia와 비교하고, NS 위임과 ACM 발급이 끝난 뒤 후속 단계를 실행한다.

```bash
scripts/build/build-admin-ui-after-ns.sh [MFA_OTP]
```

Tailnet 안에서 ArgoCD/Grafana UI에 접근하려면 Tailscale UI 연결만 별도로 실행한다.

```bash
scripts/build/connect-hub-tailscale-ui.sh [MFA_OTP]
```

기존 Spoke K3s와 IoT Secret이 살아있는 경우 factory별로 ArgoCD cluster 등록을 복구한다.

```bash
scripts/build/register-spoke-factory-a.sh [MFA_OTP]
scripts/build/register-spoke-factory-b.sh [MFA_OTP]
scripts/build/register-spoke-factory-c.sh [MFA_OTP]
```

각 factory 등록 스크립트는 아래만 수행한다.

```text
1. 해당 factory만 enabled 처리
2. Tailscale Operator 확인/설치
3. 해당 factory egress Service 생성/검증
4. 해당 factory argocd-manager RBAC/token 확인
5. Hub ArgoCD cluster Secret 생성/검증
6. AEGIS Spoke ApplicationSet repo 연결/검증
7. 해당 aegis-spoke-factory-* Application sync/wait
```

이 경로는 `register-thing.sh`와 `register-k3s-secret.sh`를 실행하지 않는다.

### 케이스 2 — Hub + IoT를 모두 다시 올릴 때

IoT Thing과 K3s Secret까지 재등록해야 하는 경우에만 `--iot`를 붙인다.

```bash
scripts/build/build-all.sh --iot [MFA_OTP]
```

Admin UI Ingress가 이미 활성화된 상태였다면:

```bash
scripts/build/build-all.sh --admin-ui-after-ns --iot [MFA_OTP]
```

### Admin UI NS 재확인

Hub를 destroy하면 Route53 Hosted Zone과 ACM Certificate가 함께 삭제된다.
Hub를 재생성하면 Hosted Zone이 새로 만들어지며 NS 값이 바뀔 수 있다.

Hub 재생성 직후 반드시 NS 값을 확인하고 Gabia와 비교한다.

```bash
cat secret/admin-ui-nameservers.txt
```

NS 값이 이전과 다르면 Gabia 관리 콘솔에서 네임서버를 업데이트한 뒤 ACM 발급을 기다린다.

```bash
scripts/build/build-admin-ui-after-ns.sh [MFA_OTP]
```

NS 값이 같으면 ACM 재검증이 빠르게 끝나거나 이미 ISSUED 상태일 수 있다.
ACM 상태는 AWS 콘솔 또는 아래 명령으로 확인한다.

```bash
aws acm list-certificates --region ap-south-1 --query 'CertificateSummaryList[*].[DomainName,Status]' --output table
```

## 단계별 단독 실행

### Hub 전체 (infra + platform)

```bash
scripts/build/build-hub.sh [MFA_OTP]
```

### Hub 인프라만 (Terraform)

EKS 재생성이나 IRSA 변경 시 사용한다. Ansible은 실행하지 않는다.

```bash
scripts/build/build-hub-infra.sh [MFA_OTP]
```

### Hub 플랫폼만 (Ansible)

EKS가 이미 실행 중인 상태에서 ArgoCD 재설치, Grafana 재설치 등 K8s 워크로드만 재적용할 때 사용한다.

```bash
scripts/build/build-hub-platform.sh [MFA_OTP]
```

특정 컴포넌트만 재실행하려면 Ansible을 직접 호출한다.

```bash
cd scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_bootstrap.yml
```

### IoT / Spoke 등록

```bash
scripts/build/build-iot-factory-a.sh [MFA_OTP]
```

Hub만 재생성한 뒤 기존 IoT Secret을 유지하면서 Spoke/Repo 연결만 복구하려면 `build-iot-factory-a.sh`가 아니라 `register-spoke-factory-a.sh`, `register-spoke-factory-b.sh`, `register-spoke-factory-c.sh`를 각각 사용한다.

## 강제 재적용 옵션

Hub Platform의 각 컴포넌트는 이미 `deployed` 상태이고 chart version이 같으면 Helm upgrade를 건너뛴다. 강제 재적용이 필요하면 환경변수를 사용한다.

```bash
FORCE_ARGOCD_UPGRADE=true scripts/build/build-hub-platform.sh
FORCE_GRAFANA_UPGRADE=true scripts/build/build-hub-platform.sh
FORCE_AWS_LB_CONTROLLER_UPGRADE=true scripts/build/build-hub-platform.sh
FORCE_TAILSCALE_OPERATOR_UPGRADE=true scripts/build/build-iot-factory-a.sh
```

## Hub-Spoke Tailscale

Hub-Spoke Tailscale과 ArgoCD cluster Secret은 각 Spoke K3s API에 직접 접근해야 하므로 `build-hub.sh` 기본 경로에서 제외한다. 대상 factory가 켜져 있고 kubeconfig로 접근 가능할 때 factory별 등록 스크립트 또는 Ansible playbook이 아래 리소스를 생성하거나 검증한다.

```text
tailscale/tailscale-operator Helm release
argocd/<factory>-master-tailnet egress Service
argocd/argocd-server-tailscale UI Service
observability/grafana-tailscale UI Service
argocd/cluster-<factory> cluster Secret
```

2026-05-20 기준 `factory-a/b/c`는 개별 등록 대상이다.

```bash
scripts/build/register-spoke-factory-a.sh [MFA_OTP]
scripts/build/register-spoke-factory-b.sh [MFA_OTP]
scripts/build/register-spoke-factory-c.sh [MFA_OTP]
```

필수 secret 파일:

```text
~/Aegis/.aegis/secrets/tailscale/operator.env
```

해당 파일에 `TAILSCALE_OAUTH_CLIENT_ID`, `TAILSCALE_OAUTH_CLIENT_SECRET`이 없으면 Hub-Spoke Tailscale 단계는 실패한다. IoT 인증서와 K3s Secret만 처리하고 Tailscale/cluster Secret을 임시로 건너뛰려면 아래처럼 실행한다.

```bash
BUILD_TAILSCALE=false scripts/build/build-iot-factory-a.sh
```

`BUILD_TAILSCALE=false`일 때 `DEPLOY_SPOKES` 기본값도 `false`가 된다. 기존 ArgoCD cluster Secret을 그대로 사용해 ApplicationSet만 다시 적용하려면 명시적으로 켠다.

```bash
BUILD_TAILSCALE=false DEPLOY_SPOKES=true scripts/build/build-iot-factory-a.sh
```

## 특정 단계 선택 실행

```bash
# Foundation만 실행
BUILD_HUB=false BUILD_FOUNDATION=true scripts/build/build-all.sh

# IoT까지 포함
scripts/build/build-all.sh --iot

# Hub만 건너뛰기
BUILD_HUB=false scripts/build/build-all.sh
```

## Admin UI NS 위임 포함 재생성 순서

Admin UI HTTPS Ingress는 기본값에서 비활성화된다. `minsoo-tech.cloud`를 Gabia에서 Route53 Hosted Zone NS로 위임하고 ACM certificate가 `ISSUED`가 된 뒤에만 Admin UI Ingress를 활성화한다.

Hub build는 Terraform apply 직후 `secret/admin-ui-nameservers.txt`를 갱신한다. Gabia에 입력할 NS는 문서에 적힌 값보다 이 파일을 우선한다.

### 1. 전체 리소스 1차 생성

이 단계에서 Hub EKS, ArgoCD, Prometheus Agent, Grafana, AWS Load Balancer Controller를 생성하고, Admin UI용 Route53 Hosted Zone NS를 출력한다. Foundation과 IoT까지 포함하려면 `--foundation`, `--iot`를 명시한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-all.sh
```

MFA OTP를 함께 넘기려면:

```bash
scripts/build/build-all.sh <MFA_OTP>
```

실행 중 아래 형식으로 Gabia에 입력할 NS가 출력된다.

```text
Set these name servers in Gabia for minsoo-tech.cloud:

ns-...
ns-...
ns-...
ns-...
```

같은 내용은 아래 파일에도 저장된다.

```text
secret/admin-ui-nameservers.txt
```

### 2. Gabia NS 입력

Gabia 관리 콘솔에서 `minsoo-tech.cloud`의 네임서버를 1단계에서 출력된 NS 4개로 변경한다.

Hosted Zone을 destroy/recreate하면 NS 값이 바뀔 수 있다. 재생성할 때마다 기존 문서나 기억한 값을 쓰지 말고, 반드시 방금 출력된 값 또는 `secret/admin-ui-nameservers.txt`를 다시 확인한다.

### 3. Admin UI HTTPS Ingress 활성화

Gabia에 NS를 저장한 뒤 아래 스크립트를 실행한다. 이 스크립트는 ACM certificate가 `ISSUED`가 될 때까지 기다린 다음 Admin UI Ingress bootstrap/verify만 실행한다.

```bash
scripts/build/build-admin-ui-after-ns.sh
```

MFA OTP를 함께 넘기려면:

```bash
scripts/build/build-admin-ui-after-ns.sh <MFA_OTP>
```

성공하면 아래 HTTPS endpoint가 출력된다.

```text
https://argocd.minsoo-tech.cloud
https://grafana.minsoo-tech.cloud
```

이미 NS 위임과 ACM 발급이 끝난 상태에서 Hub와 Admin UI를 한 번에 다시 적용해야 한다면 아래처럼 후속 단계를 포함한다.

```bash
scripts/build/build-all.sh --admin-ui-after-ns
```

IoT / Spoke 등록:

```bash
scripts/build/build-iot-factory-a.sh
```

전체 생성에서 특정 단계를 건너뛰려면 환경 변수를 사용한다.

```bash
BUILD_HUB=false scripts/build/build-all.sh
```

```bash
BUILD_HUB=false scripts/build/build-all.sh --iot
```

## 주의

- `build-all.sh`는 Hub EKS와 NAT Gateway를 생성할 수 있어 비용이 발생한다.
- Admin UI Ingress를 활성화하면 Public ALB와 ALB LCU, public IPv4 비용이 추가된다.
- Tailscale Operator 자체는 EKS 내부 Kubernetes 리소스다. EKS를 destroy하면 사라지므로 다음 `build-hub.sh` 실행 때 secret 파일을 기준으로 다시 등록한다.
- 전체 생성 범위에 대응하는 전체 삭제는 `scripts/destroy/destroy-all.sh`로 실행한다.
- ArgoCD UI port-forward는 장기 실행 프로세스이므로 전체 build에는 포함하지 않는다.
- UI 접속은 별도로 `scripts/ops/argocd-port-forward.sh`를 실행한다.
- 인증서/private key 출력은 `secret/`에만 저장되고 Git에는 들어가지 않는다.
