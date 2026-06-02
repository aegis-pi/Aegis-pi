# Destroy Scripts

상태: source of truth
기준일: 2026-05-27

## 목적

이 디렉터리는 Aegis-Pi 리소스 삭제 진입점을 순서대로 관리한다.

새 리소스를 추가하거나 기존 리소스 삭제 방식이 바뀌면 이 디렉터리의 스크립트와 문서를 함께 업데이트한다.

## 레이어 구분

build와 대칭되는 4개 레이어로 관리한다.

```text
Layer -1│ VM Data      │ factory-b/c dummy generator systemd service. data-pipeline 삭제 전 정지 권장.
        │              │ legacy local publisher unit이 있으면 함께 정지.
Layer 0a│ Data-pipeline│ IoT Rule × 3, Lambda(DataProcessor/GraphAggregator/CloudInfra/RiskAlertDispatcher),
        │              │ S3 processed alert trigger, Slack secret metadata, CloudWatch, IAM. 기본 삭제 흐름에 포함.
        │              │ DESTROY_DATA_PIPE=false로 제외 가능. foundation S3/DynamoDB data source 참조
        │              │ 때문에 foundation destroy 이전에 반드시 먼저 삭제해야 함.
Layer 0a│ Reporting    │ EventBridge Scheduler, Step Functions, reporting Lambda, CloudWatch, IAM.
        │              │ foundation S3 data source를 참조하므로 foundation destroy 이전에 먼저 삭제해야 함.
Layer 0b│ Foundation   │ 영구 리소스(S3, ECR, DynamoDB, Admin UI Route53/ACM).
        │              │ 기본 제외. DESTROY_FOUNDATION=true 필요.
Layer 1 │ Hub Infra    │ VPC, EKS, IRSA (Terraform destroy)
Layer 2 │ Hub Platform │ ALB 등 K8s Controller가 만든 AWS 리소스 선정리 (Ansible cleanup)
Layer 3 │ IoT          │ IoT Thing/Policy/Certificate, K3s Secret
```

## 삭제 순서

순서가 중요하다. ALB는 K8s Ingress를 통해 만들어진 AWS 리소스이므로 Terraform destroy 전에
반드시 먼저 정리해야 한다. 그렇지 않으면 ALB가 VPC를 붙잡고 있어 Terraform destroy가 실패한다.

```text
0. VM dummy generator stop
   - factory-b/c VM worker의 local dummy generator systemd service 정지
   - legacy local dummy publisher systemd unit이 있으면 함께 정지
   - data-pipeline이 내려간 뒤에도 outbox가 계속 쌓이는 것을 방지
   - IoT Core Thing/certificate, K3s Secret은 건드리지 않음

0.5. data-pipeline destroy (기본 포함, DESTROY_DATA_PIPE=false로 제외 가능)
   - infra/data-pipeline Terraform destroy
   - IoT Rule × 3, Lambda, Scheduler, S3 processed alert notification, Slack webhook secret metadata,
     CloudWatch log group, IAM role/policy 삭제
   - DynamoDB 데이터는 foundation에 보존됨
   - ⚠️ foundation destroy 이전에 반드시 먼저 실행. 역순이면 terraform destroy 실패

0.6. reporting destroy (필요 시 명시 실행)
   - infra/reporting Terraform destroy
   - Scheduler, Step Functions, reporting Lambda, IAM role/policy, CloudWatch log group 삭제
   - S3 reports/daily 산출물은 삭제하지 않음
   - foundation destroy 이전에 먼저 실행

1. K3s factory-a IoT Secret 사전 삭제
   - DESTROY_IOT=true일 때 AWS MFA 전에 SSH로 K3s Secret 삭제
   - 이후 IoT destroy 단계에서는 같은 Secret 삭제를 건너뜀

2. iot factory-a
   - IoT certificate detach/delete
   - IoT Policy 삭제
   - IoT Thing 삭제

3. hub-platform cleanup  ← Terraform destroy 전에 반드시 먼저 실행
   - EKS가 살아있는 경우에만 실행
   - Ansible hub_admin_ingress_cleanup.yml (Ingress 삭제 → ALB 자동 제거)
   - Tailscale Kubernetes 리소스는 별도 cleanup하지 않음 (EKS 삭제와 함께 사라짐)

4. hub-infra
   - infra/hub Terraform destroy
   - EKS, VPC, node group, NAT Gateway 삭제
   - IRSA IAM role/policy 삭제 (LB Controller, Risk Normalizer)
   - Route53 Hosted Zone, ACM certificate는 foundation에 보존
   - infra/hub가 Foundation outputs를 참조하므로 foundation tfstate 필요

5. foundation (기본 제외, 명시적 실행 필요)
   - infra/foundation Terraform destroy
   - S3 data bucket, ECR, DynamoDB, GitHub Actions OIDC, Admin UI Route53/ACM
   - ⚠️ data-pipeline이 먼저 삭제된 상태여야 함
```

## 파일

| 파일 | 내용 |
| --- | --- |
| `stop-dummy-generators.sh` | factory-b/c VM worker의 dummy generator systemd service 정지. 인수 없이 실행하면 b/c 동시 정지. |
| `destroy-data-pipe.sh` | `infra/data-pipeline` Terraform destroy. IoT Rules × 3, Lambda/Scheduler, RiskAlertDispatcher S3 trigger, Slack webhook secret metadata, IAM 삭제. DynamoDB는 보존. state file 없으면 no-op. |
| `destroy-reporting.sh` | `infra/reporting` Terraform destroy. Scheduler, Step Functions, reporting Lambda, IAM, Log Group 삭제. state file 없으면 no-op. |
| `destroy-all.sh` | 기본: data-pipeline → hub(platform cleanup → infra) 삭제. IoT/Foundation은 명시 플래그 필요. DESTROY_DATA_PIPE=false로 data-pipe 제외 가능. |
| `destroy-hub.sh` | `destroy-hub-platform.sh` → `destroy-hub-infra.sh` 순서 실행 wrapper |
| `destroy-hub-platform.sh` | Ansible cleanup (Ingress → ALB 삭제). Terraform destroy 전에 실행. |
| `destroy-hub-infra.sh` | `infra/hub` Terraform destroy (EKS, VPC, IRSA 등) |
| `destroy-foundation.sh` | Foundation 영속 리소스 삭제. `DESTROY_FOUNDATION=true` 필요. |
| `destroy-iot-factory-a.sh` | `factory-a` K3s Secret과 IoT 리소스 삭제 |
| `destroy-k3s-iot-secret.sh` | K3s Secret만 삭제 |

## 개발 단계 삭제 범위 가이드

개발 중에는 비용을 최소화하면서 데이터와 상태를 보존하는 것이 목표다.
아래 표를 기준으로 상황에 맞는 삭제 범위를 선택한다.

### 리소스별 월 비용 및 삭제 권장 여부

```text
리소스                          월 비용(추정)    개발 중단 시 삭제 여부
──────────────────────────────────────────────────────────────────
EKS 컨트롤 플레인               ~$73            ✓ 삭제 (Hub Infra)
EC2 노드 t3.medium × 2         ~$61            ✓ 삭제 (Hub Infra)
NAT Gateway × 1                ~$41            ✓ 삭제 (Hub Infra)
ALB (Admin Ingress 활성화 시)  ~$16+           ✓ 삭제 (Hub Platform cleanup)
EIP × 1                        ~$4             ✓ 삭제 (Hub Infra)
Lambda (data-processor)        ~$0             △ 삭제 권장 (Data-pipeline destroy)
IoT Rules × 3                  ~$0             △ 삭제 권장 (Data-pipeline destroy)
CloudWatch log group           ~$0             △ 삭제 권장 (Data-pipeline destroy)
──────────────────────────────────────────────────────────────────
DynamoDB (FactoryStatus)       ~$0             ✗ 보존 (foundation 영구 리소스)
S3 data bucket                 ~$1-3           ✗ 보존 (데이터 손실 방지)
ECR 리포지토리                  ~$0.06          ✗ 보존 (이미지 이력 보존)
IoT Thing/Policy/Certificate   ~$0             ✗ 보존 (재등록 번거로움 대비 비용 없음)
K3s Secret                     $0              ✗ 보존 (Pi에 존재, 비용 없음)
Route53 Hosted Zone            ~$0.5           △ 보존 권장 (NS 재위임 절차 번거로움)
ACM Certificate                $0              ✗ 보존 (재발급 + ACM 검증 대기 필요)
```

### 권장 삭제 범위

**개발 중단 시 (일반)** — Hub만 내린다. Foundation과 IoT는 그대로 유지.

```text
삭제: VM dummy generator 정지 → Data-pipeline (IoT Rules, Lambda) → Hub Platform (ALB) → Hub Infra (EKS, NAT GW, VPC)
보존: Foundation(S3, ECR, DynamoDB), IoT Thing/Certificate, Spoke K3s Secret
절약: ~$200/월
재개: build-hub.sh + build-data-pipe.sh 이후 UI/Spoke 등록 스크립트를 단계별 실행
```

```bash
# VM 데이터 생성 정지
scripts/destroy/stop-dummy-generators.sh

# Data-pipeline + Hub 삭제, Foundation/IoT 보존 (기본 동작)
scripts/destroy/destroy-all.sh [MFA_OTP]

# 단독 진입점 (순서 중요)
scripts/destroy/destroy-data-pipe.sh [MFA_OTP]
scripts/destroy/destroy-hub.sh [MFA_OTP]

# 재개 시 최소 Hub 복구
scripts/build/build-hub.sh [MFA_OTP]
scripts/build/build-data-pipe.sh [MFA_OTP]
```

**완전 초기화 시** — 프로젝트를 처음부터 다시 시작해야 할 때만 사용한다.

```text
삭제: IoT → Hub → Foundation (S3 데이터 포함 전체 삭제)
주의: S3 데이터, ECR 이미지 복구 불가
```

```bash
DESTROY_IOT=true DESTROY_FOUNDATION=true scripts/destroy/destroy-all.sh [MFA_OTP]
```

### IoT를 삭제하지 않아도 되는 이유

IoT Thing/Policy/Certificate는 AWS 과금이 사실상 없다 (수백만 건 메시지 기준 수 센트 수준).
K3s Secret은 라즈베리파이에 존재하며 AWS 비용이 전혀 없다.
삭제 후 재등록하면 새 인증서가 발급되어 K3s Secret도 다시 등록해야 하므로 그냥 유지하는 것이 낫다.

## 일반 개발 중단 (Hub 삭제, Foundation/IoT 보존)

개발을 중단할 때 비용이 나가는 Hub 리소스만 내린다. Foundation(S3 데이터, ECR 이미지, DynamoDB)과 IoT Thing/certificate/K3s Secret은 보존된다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi

# 1. VM worker의 dummy generator 정지
scripts/destroy/stop-dummy-generators.sh

# 2. Hub 삭제
scripts/destroy/destroy-all.sh [MFA_OTP]
```

`destroy-all.sh`의 기본 동작:

```text
DESTROY_IOT=false       ← IoT는 기본 보존
DESTROY_HUB=true
DESTROY_FOUNDATION=false
```

`DESTROY_IOT=true`를 명시했을 때만 AWS MFA 입력 전에 `scripts/destroy/destroy-k3s-iot-secret.sh`를 실행한다. 이 단계에서 OpenSSH가 `minsoo@10.10.10.10` 비밀번호를 물을 수 있다.

## 단계별 단독 실행

### VM dummy generator 정지

Hub 삭제 전에 factory-b/c worker의 systemd generator를 멈춘다. 접속 정보는 `scripts/ops/dummy-generators.env`를 기본으로 사용하며, `AEGIS_DUMMY_GENERATORS_ENV`로 다른 파일을 지정할 수 있다. 현재 표준 publish 경로는 K3s `edge-iot-publisher`이므로 로컬 publisher는 설치돼 있지 않은 것이 정상이다. 다만 과거 legacy local publisher unit이 남아 있으면 stop 단계에서 함께 멈춘다.

```bash
scripts/destroy/stop-dummy-generators.sh
```

특정 factory만 멈추려면:

```bash
scripts/destroy/stop-dummy-generators.sh factory-b
scripts/destroy/stop-dummy-generators.sh factory-c
```

### Hub 전체 삭제 (platform cleanup → infra)

```bash
scripts/destroy/destroy-hub.sh [MFA_OTP]
```

### Hub Platform cleanup만 (ALB 선정리)

Terraform destroy 전 ALB를 미리 정리할 때 사용한다.

```bash
scripts/destroy/destroy-hub-platform.sh [MFA_OTP]
```

### Hub Infra만 삭제 (Terraform)

platform cleanup이 완료된 후 실행한다.

```bash
scripts/destroy/destroy-hub-infra.sh [MFA_OTP]
```

### IoT만 삭제

```bash
scripts/destroy/destroy-iot-factory-a.sh [MFA_OTP]
```

### K3s Secret만 삭제

```bash
scripts/destroy/destroy-k3s-iot-secret.sh
```

### Foundation 삭제 (명시적 플래그 필수)

S3 데이터와 ECR 이미지가 모두 삭제된다. 복구 불가.

```bash
DESTROY_FOUNDATION=true scripts/destroy/destroy-foundation.sh [MFA_OTP]
```

완전 삭제(Foundation 포함)가 필요하면:

```bash
DESTROY_IOT=true DESTROY_FOUNDATION=true scripts/destroy/destroy-all.sh [MFA_OTP]
```

## Hub + Data-pipeline 재생성 시 전체 흐름

Hub와 data-pipeline을 내렸다가 다시 올리는 경우:

```bash
# 내리기 (순서 중요: data-pipe → hub)
scripts/destroy/stop-dummy-generators.sh
scripts/destroy/destroy-data-pipe.sh [MFA_OTP]
scripts/destroy/destroy-hub.sh [MFA_OTP]

# 올리기 (순서 중요: hub → data-pipe → register)
scripts/build/build-hub.sh [MFA_OTP]
scripts/build/build-data-pipe.sh [MFA_OTP]
scripts/build/build-admin-ui-after-ns.sh [MFA_OTP]
scripts/build/register-spoke-factory-a.sh [MFA_OTP]
scripts/build/register-spoke-factory-b.sh [MFA_OTP]
scripts/build/register-spoke-factory-c.sh [MFA_OTP]
scripts/ops/manage-dummy-generators.sh start factory-b
scripts/ops/manage-dummy-generators.sh start factory-c
```

## Hub-only 비용 절감 + 데이터 수집 유지 흐름

데이터를 계속 쌓아야 하는 개발 기간에는 data-pipeline과 Spoke K3s workload를 유지하고 Hub만 내린다. 이 흐름에서는 `destroy-all.sh`를 쓰지 않는다. `destroy-all.sh`의 기본값은 `DESTROY_DATA_PIPE=true`라 IoT Rule과 Lambda data processor까지 삭제하기 때문이다.

```bash
# 퇴근 시
scripts/destroy/destroy-hub.sh [MFA_OTP]

# 출근 시
scripts/build/build-hub.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-a.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-b.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-c.sh [MFA_OTP]
scripts/ops/check-spoke-publisher-safety.sh
```

이 모드에서는 `stop-dummy-generators.sh`를 실행하지 않는다. factory-b/c dummy generator와 Spoke K3s `edge-iot-publisher`가 계속 동작해야 밤새 데이터가 누적된다.

`HUB_ONLY_RECONNECT=true`는 register 단계에서 ArgoCD `app sync`와 ECR pull secret refresh/restart를 기본 비활성화한다. 기존 Spoke Deployment를 Hub ArgoCD에 다시 붙이되, 불필요한 rollout을 피하기 위한 모드다.

## 주의

- `destroy-all.sh`는 Hub EKS와 NAT Gateway를 삭제한다.
- `destroy-hub.sh`는 Terraform destroy 전에 반드시 `destroy-hub-platform.sh`(Ingress cleanup)를 먼저 실행한다. Ingress가 비활성화 상태면 cleanup은 no-op에 가깝게 지나간다.
- `destroy-hub.sh`는 Tailscale OAuth client, Tailscale Admin Console device, `factory-a-master` Tailscale 상태를 삭제하거나 revoke하지 않는다.
- `factory-a-master` Tailscale은 라즈베리파이 OS 레벨 상태이므로 비용이 없고 유지한다.
- Hub를 다시 올린 뒤 ALB/Admin UI HTTPS는 `scripts/build/build-admin-ui-after-ns.sh`, Tailnet UI가 필요할 때는 `scripts/build/connect-hub-tailscale-ui.sh`, factory별 Spoke 등록은 `scripts/build/register-spoke-factory-a.sh`, `scripts/build/register-spoke-factory-b.sh`, `scripts/build/register-spoke-factory-c.sh`가 `~/Aegis/.aegis/secrets/tailscale/operator.env`를 사용해 생성/검증한다.
- 기존 Spoke workload를 유지하는 재연결에서는 `HUB_ONLY_RECONNECT=true`를 사용한다. GitOps 변경을 반영해야 할 때만 `SYNC_SPOKE_APP=true`를 명시한다.
- `scripts/ops/check-spoke-publisher-safety.sh`로 `edge-iot-publisher` Deployment가 `Recreate` 전략이고 running pod가 factory별 1개 이하인지 확인한다.
- `destroy-hub-infra.sh`는 `infra/hub`가 Foundation outputs를 참조하므로 `infra/foundation/terraform.tfstate`가 있어야 한다.
- CLI로 만든 IoT 리소스는 Terraform state에 없으므로 이 디렉터리의 destroy 스크립트로 정리한다.
- K3s Secret은 Terraform state에 없으므로 SSH 기반 `kubectl delete secret`로 정리한다.
- SSH 비밀번호는 스크립트가 저장하지 않는다. 반복 입력을 피하려면 운영 PC와 `factory-a-master` 사이에 SSH key 인증을 구성한다.
