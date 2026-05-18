# Destroy Scripts

상태: source of truth
기준일: 2026-05-18

## 목적

이 디렉터리는 Aegis-Pi 리소스 삭제 진입점을 순서대로 관리한다.

새 리소스를 추가하거나 기존 리소스 삭제 방식이 바뀌면 이 디렉터리의 스크립트와 문서를 함께 업데이트한다.

## 레이어 구분

build와 대칭되는 4개 레이어로 관리한다.

```text
Layer 0 │ Foundation   │ 영구 리소스. 기본 삭제 흐름에서 제외. DESTROY_FOUNDATION=true 명시 필요.
Layer 1 │ Hub Infra    │ VPC, EKS, IRSA, Route53, ACM (Terraform destroy)
Layer 2 │ Hub Platform │ ALB 등 K8s Controller가 만든 AWS 리소스 선정리 (Ansible cleanup)
Layer 3 │ IoT          │ IoT Thing/Policy/Certificate, K3s Secret
```

## 삭제 순서

순서가 중요하다. ALB는 K8s Ingress를 통해 만들어진 AWS 리소스이므로 Terraform destroy 전에
반드시 먼저 정리해야 한다. 그렇지 않으면 ALB가 VPC를 붙잡고 있어 Terraform destroy가 실패한다.

```text
0. K3s factory-a IoT Secret 사전 삭제
   - DESTROY_IOT=true일 때 AWS MFA 전에 SSH로 K3s Secret 삭제
   - 이후 IoT destroy 단계에서는 같은 Secret 삭제를 건너뜀

1. iot factory-a
   - IoT certificate detach/delete
   - IoT Policy 삭제
   - IoT Thing 삭제

2. hub-platform cleanup  ← Terraform destroy 전에 반드시 먼저 실행
   - EKS가 살아있는 경우에만 실행
   - Ansible hub_admin_ingress_cleanup.yml (Ingress 삭제 → ALB 자동 제거)
   - Tailscale Kubernetes 리소스는 별도 cleanup하지 않음 (EKS 삭제와 함께 사라짐)

3. hub-infra
   - infra/hub Terraform destroy
   - EKS, VPC, node group, NAT Gateway 삭제
   - IRSA IAM role/policy 삭제 (LB Controller, Grafana, Prometheus, Risk Normalizer)
   - Route53 Hosted Zone, ACM certificate 삭제
   - infra/hub가 Foundation outputs를 참조하므로 foundation tfstate 필요

4. foundation (기본 제외, 명시적 실행 필요)
   - infra/foundation Terraform destroy
   - S3 data bucket, AMP Workspace, ECR, IoT Rule, GitHub Actions OIDC
```

## 파일

| 파일 | 내용 |
| --- | --- |
| `destroy-all.sh` | 기본 hub(platform cleanup → infra) 삭제 실행. IoT와 Foundation은 명시 플래그가 있을 때만 삭제. |
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
NAT Gateway × 2                ~$64            ✓ 삭제 (Hub Infra)
ALB (Admin Ingress 활성화 시)  ~$16+           ✓ 삭제 (Hub Platform cleanup)
EIP × 2                        ~$7             ✓ 삭제 (Hub Infra)
──────────────────────────────────────────────────────────────────
S3 data bucket                 ~$1-3           ✗ 보존 (데이터 손실 방지)
AMP Workspace                  ~$5-20          ✗ 보존 (메트릭 이력 보존)
ECR 리포지토리                  ~$0.1           ✗ 보존 (이미지 이력 보존)
IoT Thing/Policy/Certificate   ~$0             ✗ 보존 (재등록 번거로움 대비 비용 없음)
K3s Secret                     $0              ✗ 보존 (Pi에 존재, 비용 없음)
Route53 Hosted Zone            ~$0.5           △ 보존 권장 (NS 재위임 절차 번거로움)
ACM Certificate                $0              ✗ 보존 (재발급 + ACM 검증 대기 필요)
```

### 권장 삭제 범위

**개발 중단 시 (일반)** — Hub만 내린다. Foundation과 IoT는 그대로 유지.

```text
삭제: Hub Platform (ALB) → Hub Infra (EKS, NAT GW, VPC)
보존: Foundation, IoT Thing/Certificate, K3s Secret
절약: ~$200/월
재개: build-hub.sh 한 번으로 복구 (약 20-30분)
```

```bash
# Hub 삭제, Foundation/IoT 보존 (기본 동작)
scripts/destroy/destroy-all.sh [MFA_OTP]

# 동일한 Hub-only 단독 진입점
scripts/destroy/destroy-hub.sh [MFA_OTP]

# 재개 시
scripts/build/build-hub.sh [MFA_OTP]
```

**완전 초기화 시** — 프로젝트를 처음부터 다시 시작해야 할 때만 사용한다.

```text
삭제: IoT → Hub → Foundation (S3 데이터 포함 전체 삭제)
주의: S3 데이터, AMP 메트릭, ECR 이미지 복구 불가
```

```bash
DESTROY_IOT=true DESTROY_FOUNDATION=true scripts/destroy/destroy-all.sh [MFA_OTP]
```

### IoT를 삭제하지 않아도 되는 이유

IoT Thing/Policy/Certificate는 AWS 과금이 사실상 없다 (수백만 건 메시지 기준 수 센트 수준).
K3s Secret은 라즈베리파이에 존재하며 AWS 비용이 전혀 없다.
삭제 후 재등록하면 새 인증서가 발급되어 K3s Secret도 다시 등록해야 하므로 그냥 유지하는 것이 낫다.

## 일반 개발 중단 (Hub 삭제, Foundation/IoT 보존)

개발을 중단할 때 비용이 나가는 Hub 리소스만 내린다. Foundation(S3 데이터, AMP 메트릭, ECR 이미지)과 IoT Thing/certificate/K3s Secret은 보존된다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
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

S3 데이터, AMP 메트릭, ECR 이미지가 모두 삭제된다. 복구 불가.

```bash
DESTROY_FOUNDATION=true scripts/destroy/destroy-foundation.sh [MFA_OTP]
```

완전 삭제(Foundation 포함)가 필요하면:

```bash
DESTROY_IOT=true DESTROY_FOUNDATION=true scripts/destroy/destroy-all.sh [MFA_OTP]
```

## Hub 재생성 시 전체 흐름

Hub를 내렸다가 다시 올리는 경우:

```bash
# 내리기
scripts/destroy/destroy-hub.sh [MFA_OTP]

# 올리기
scripts/build/build-hub.sh [MFA_OTP]
```

## 주의

- `destroy-all.sh`는 Hub EKS와 NAT Gateway를 삭제한다.
- `destroy-hub.sh`는 Terraform destroy 전에 반드시 `destroy-hub-platform.sh`(Ingress cleanup)를 먼저 실행한다. Ingress가 비활성화 상태면 cleanup은 no-op에 가깝게 지나간다.
- `destroy-hub.sh`는 Tailscale OAuth client, Tailscale Admin Console device, `factory-a-master` Tailscale 상태를 삭제하거나 revoke하지 않는다.
- `factory-a-master` Tailscale은 라즈베리파이 OS 레벨 상태이므로 비용이 없고 유지한다.
- Hub를 다시 올리면 `scripts/build/build-hub-platform.sh`가 `~/Aegis/.aegis/secrets/tailscale/operator.env`를 사용해 Tailscale Operator와 관련 리소스를 다시 생성/검증한다.
- `destroy-hub-infra.sh`는 `infra/hub`가 Foundation outputs를 참조하므로 `infra/foundation/terraform.tfstate`가 있어야 한다.
- CLI로 만든 IoT 리소스는 Terraform state에 없으므로 이 디렉터리의 destroy 스크립트로 정리한다.
- K3s Secret은 Terraform state에 없으므로 SSH 기반 `kubectl delete secret`로 정리한다.
- SSH 비밀번호는 스크립트가 저장하지 않는다. 반복 입력을 피하려면 운영 PC와 `factory-a-master` 사이에 SSH key 인증을 구성한다.
