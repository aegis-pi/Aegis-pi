# Session State

상태: working tracker
기준일: 2026-04-30

## 목적

이 파일은 현재 작업 세션의 이어받기용 기록이다. `docs/issues/MASTER_CHECKLIST.md`와 각 M0~M7 이슈 문서가 공식 진행 기준이고, 이 파일은 지금까지 한 일과 다음에 할 일을 빠르게 복구하기 위한 보조 문서다.

이 파일은 누적 로그가 아니라 현재 상태 스냅샷으로 관리한다. 사용자가 "문서 최신화" 또는 "세션 저장"을 요청하면 아래 섹션을 덧붙이는 방식이 아니라 현재 기준으로 갱신한다.

## 마일스톤 기준 진행 현황

| 마일스톤 | 이슈 | 상태 | 기준 문서 |
| --- | --- | --- | --- |
| M0 | Issue 1 - Safe-Edge/OS | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 2 - Safe-Edge/네트워크 | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 3 - Safe-Edge/K3s | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 4 - Safe-Edge/MetalLB | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 5 - Safe-Edge/Longhorn | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 6 - Safe-Edge/NFS | 보류 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 7 - 배포/ArgoCD | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 8 - 관제/Grafana | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 9 - 데이터/BME280 | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 10 - Safe-Edge/AI | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 11 - Safe-Edge/Failover | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 12 - 자동화/Ansible | 부분 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 13 - 검증/통합 | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M1 | Issue 0 - AWS/Auth | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 1 - Hub/EKS | 진행 중 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 2 - Hub/Kubernetes | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 3 - Hub/ArgoCD | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 4 - Hub/S3 | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 5 - Hub/IoT Core | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 6 - 관제/AMP | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 6A - 관제/Dashboard VPC | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 7 - 관제/Prometheus | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 8 - 관제/Grafana | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 9 - Risk/Config | 대기 | `docs/issues/M1_hub-cloud.md` |

현재 바로 이어서 할 이슈:

```text
M1 Issue 1 - [Hub/EKS] 클러스터 생성 및 기본 설정
```

## 현재 큰 상태

```text
현재 단계: M1 Hub 클라우드 기반 구성
완료: M0 factory-a Safe-Edge 기준선
완료: M1 Issue 0 AWS CLI MFA 및 Terraform 접근 설정
진행 중: M1 Issue 1 EKS/VPC 설계 및 Terraform skeleton
완료: Safe-Edge start_test Ansible playbook
AWS 실제 리소스 생성: 아직 없음
Terraform apply 실행 여부: 아직 안 함
```

## 지금까지 완료한 일

### M0 factory-a 기준선

- Raspberry Pi 3-node K3s `factory-a` 기준선 구축 및 검증 완료
- ArgoCD, Longhorn, MetalLB, monitoring, ai-apps 기준선 정리
- AI snapshot 저장 기준을 Longhorn PVC에서 node-local hostPath로 변경한 현재 운영 기준 반영
- AI 추론 결과는 InfluxDB PVC를 통해 Longhorn에 저장하는 기준 반영
- failover/failback 테스트 결과 및 트러블슈팅 문서 확장
- 변경된 계획 추적용 `docs/changes/` 문서 추가
- `start_test` 반복 점검용 Ansible playbook 추가

### Dashboard VPC 확장 방향

- 관리자 대시보드는 Tailscale에 직접 의존하지 않는 별도 Dashboard VPC 방향으로 정리
- Dashboard VPC는 Processing VPC와 VPC Peering/TGW 없이 S3/latest status store를 read-only IAM으로 조회하는 방향 확정
- Edge Agent가 센서/시스템/장치/워크로드/pipeline heartbeat 상태를 함께 보내야 한다는 기준 반영
- 관련 문서: `docs/planning/07_dashboard_vpc_extension_plan.md`

### AWS CLI MFA 및 Terraform 접근

- 로컬 WSL 환경에서 AWS CLI, Terraform, jq를 프로젝트 로컬 `.tools` 아래에 설치
- `.bashrc`에 Aegis AWS 환경 로더 등록
- `aws configure` 기본 프로필 구성 완료
- MFA ARN을 `mfa.cfg`에 구성 완료
- `mfa <OTP>` 실행 및 `aws sts get-caller-identity` 확인 완료
- 기본 AWS 리전은 `ap-south-1`
- 관련 문서: `docs/planning/08_aws_cli_mfa_terraform_access.md`

### M1 Issue 1 EKS/VPC 설계

- EKS/VPC Decision Record 작성
- Terraform skeleton 작성
- VPC/EKS 공식 Terraform module 사용
- `terraform init -backend=false` 완료
- `terraform validate` 통과
- `terraform fmt` 통과
- AWS 실제 리소스는 아직 생성하지 않음

관련 문서:

- `docs/planning/09_m1_eks_vpc_decision_record.md`
- `infra/hub/README.md`
- `infra/hub/*.tf`

## 현재 로컬 Terraform 기준

```text
Terraform root: infra/hub
Region: ap-south-1
VPC: 신규 생성
VPC CIDR: 10.40.0.0/16
AZ: 2개
Subnets: public 2개 + private 2개
NAT Gateway: single NAT Gateway
EKS endpoint: public endpoint
EKS endpoint CIDR: 0.0.0.0/0 (MVP bootstrap 임시 기준)
Node subnet: private subnet
Node group: EKS Managed Node Group
Instance type: t3.medium 기본
Node count: min/desired/max 2
Capacity: On-Demand
```

`t3.micro`는 사용하지 않는 기준이다. EKS system pod, CNI, CoreDNS, ArgoCD/Grafana/관측 컴포넌트까지 고려하면 메모리 여유가 작아 Hub MVP 기준선으로 부적합하다고 판단했다.

## 현재 AWS 상태

```text
AWS 계정 연결: MFA 세션으로 확인 완료
AWS 리소스 생성: 아직 없음
terraform apply: 아직 실행 안 함
terraform destroy 필요 여부: 현재는 생성한 리소스가 없으므로 아직 없음
```

주의:

- `terraform init`은 provider/module을 로컬에 내려받는 작업이라 AWS 리소스를 만들지 않는다.
- AWS 리소스가 실제로 만들어지는 시점은 `terraform apply` 실행 시점이다.
- 테스트가 끝나면 반드시 `terraform destroy`로 EKS, NAT Gateway, node group을 제거한다.

## 다음에 할 일

### 1. MFA 세션 확인

```bash
source ~/.bashrc
mfa <OTP>
unset AWS_PROFILE
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION=ap-south-1
aws sts get-caller-identity
```

### 2. Terraform 변수 파일 생성

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
cp terraform.tfvars.example terraform.tfvars
```

현재 MVP 기준은 `0.0.0.0/0`이므로 public IP `/32` 수정은 필요 없다. 단, 운영 전에는 반드시 좁힌다.

### 3. Terraform plan 확인

```bash
terraform init
terraform validate
terraform plan
```

`plan` 결과에서 VPC, subnet, NAT Gateway, EKS cluster, managed node group이 생성 대상으로 보이는지 확인한다.

### 4. 사용자 확인 후 apply

```bash
terraform apply
```

`apply`는 비용이 발생하는 AWS 리소스를 실제로 만든다. 실행 전 사용자 확인을 받고 진행한다.

### 5. EKS 접근 확인

```bash
aws eks update-kubeconfig --region ap-south-1 --name aegis-pi-hub-mvp
kubectl get nodes
kubectl cluster-info
```

이 단계가 성공하면 M1 Issue 1의 주요 구현 항목이 완료된다.

### 6. 테스트 종료 후 destroy

```bash
terraform destroy
```

장시간 사용하지 않을 리소스를 남기지 않는다. EKS control plane, NAT Gateway, managed node group은 켜져 있는 동안 비용이 발생한다.

## 다음 문서 업데이트 대상

`terraform apply`와 EKS 접근 확인이 끝나면 다음 문서를 갱신한다.

- `docs/issues/M1_hub-cloud.md`
- `docs/issues/MASTER_CHECKLIST.md`
- `docs/planning/09_m1_eks_vpc_decision_record.md`
- `infra/hub/README.md`

완료 처리할 수 있는 항목:

- M1 Issue 1 - EKS 클러스터 생성
- M1 Issue 1 - 노드그룹 구성
- M1 Issue 1 - `kubectl` 로컬 접근 설정
- M1 Issue 1 - EKS Add-on 설치
- M1 Issue 1 - IAM OIDC Provider 연결

## 주의사항

- Access Key, Secret Access Key, Session Token, MFA OTP, SSH 비밀번호는 문서에 기록하지 않는다.
- `terraform.tfvars`는 Git에 커밋하지 않는다.
- `infra/hub/.terraform/`은 Git에 커밋하지 않는다.
- `infra/hub/.terraform.lock.hcl`은 provider lock을 위해 커밋 대상이다.
- `terraform apply` 전에는 항상 `terraform plan`을 먼저 확인한다.
- `terraform destroy`는 실험 종료 절차로 함께 수행한다.

## 최근 커밋

```text
f41d1f3 Add Ansible start_test automation
44cf3cc Expand Safe-Edge troubleshooting notes
f8ed233 Document dashboard VPC and AWS MFA setup
```

현재 세션 정리 내용:

```text
M1 Issue 1 EKS/VPC Decision Record
infra/hub Terraform skeleton
EKS endpoint 0.0.0.0/0 MVP bootstrap 기준
테스트 후 terraform destroy 원칙
SESSION_STATE.md
```

## 갱신 규칙

- 이 파일은 새 내용을 아래에 계속 추가하지 않는다.
- 세션 저장 요청이 오면 `마일스톤 기준 진행 현황`, `현재 큰 상태`, `지금까지 완료한 일`, `현재 AWS 상태`, `다음에 할 일`, `현재 세션 정리 내용`을 현재 기준으로 갱신한다.
- 오래된 완료 기록이 현재 판단에 불필요하면 요약으로 줄인다.
- 공식 체크 여부는 항상 `docs/issues/MASTER_CHECKLIST.md`와 각 M0~M7 이슈 문서를 우선한다.
