# Session State

상태: working tracker
기준일: 2026-05-04

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
| M1 | Issue 1 - Hub/EKS | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 2 - Hub/Kubernetes | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 3 - Hub/ArgoCD | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 4 - Hub/S3 | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 5 - Hub/IoT Core | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 6 - 관제/AMP | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 6A - 관제/Dashboard VPC | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 7 - 관제/Prometheus | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 8 - 관제/Grafana | 대기 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 9 - Risk/Config | 대기 | `docs/issues/M1_hub-cloud.md` |

현재 바로 이어서 할 이슈:

```text
M1 Issue 4 - [Hub/S3] 버킷 생성 및 경로 파티셔닝 설계
```

## 현재 큰 상태

```text
현재 단계: M1 Hub 클라우드 기반 구성
완료: M0 factory-a Safe-Edge 기준선
완료: M1 Issue 0 AWS CLI MFA 및 Terraform 접근 설정
완료: M1 Issue 1 EKS/VPC Terraform apply 및 kubectl 접근 확인
완료: M1 Issue 2 Hub Kubernetes 네임스페이스 설계 및 생성
완료: M1 Issue 3 Hub ArgoCD 설치 및 CLI/UI 검증, Ansible bootstrap 전환
완료: Safe-Edge start_test Ansible playbook
확정: Terraform = 인프라, Ansible = 설정/소프트웨어/bootstrap, GitHub Actions = CI, GitHub+ArgoCD = CD
AWS 실제 리소스 생성: 테스트 후 destroy 완료, 현재 비활성
Terraform apply 실행 여부: infra/hub apply 검증 완료 후 destroy 완료
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

### M1 Issue 1 EKS/VPC 설계 및 적용

- EKS/VPC Decision Record 작성
- Terraform skeleton 작성
- VPC/subnet/NAT/route table은 직접 AWS 리소스로 관리하고, EKS는 공식 Terraform module 사용
- `terraform init -backend=false` 완료
- `terraform validate` 통과
- `terraform fmt` 통과
- `terraform plan -out=tfplan` 확인
- `terraform apply -auto-approve tfplan` 완료
- 기존 `aegis-pi-hub-mvp` 인프라를 `terraform destroy -auto-approve`로 제거
- 새 네이밍/버전 기준으로 `terraform apply -auto-approve tfplan` 완료
- `aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS` 완료
- `kubectl v1.34.7`을 `/home/vicbear/Aegis/.tools/bin/kubectl`에 설치
- `kubectl get nodes`에서 worker node 2대 `Ready` 확인
- `kubectl cluster-info`에서 EKS control plane과 CoreDNS 응답 확인
- 리소스 네이밍 규칙을 `AEGIS-[resource]-[feature]-[zone]`로 고정
- Terraform EKS 이름은 `AEGIS-EKS`, Kubernetes 버전은 `1.34`
- Issue 2 namespace/LimitRange 적용 후 최소 분리 작업을 위해 테스트용 Hub 리소스를 `terraform destroy -auto-approve`로 제거
- 책임 범위를 `infra/hub`, `scripts/ansible`, `infra/foundation` 기준으로 분리

관련 문서:

- `docs/planning/09_m1_eks_vpc_decision_record.md`
- `docs/planning/11_delivery_ownership_flow.md`
- `infra/hub/README.md`
- `infra/hub/*.tf`

## 현재 로컬 Terraform 기준

```text
Terraform roots:
- infra/hub: VPC, subnet, NAT Gateway, EKS cluster, node group
- infra/foundation: S3, ECR, AMP, IoT Core처럼 EKS destroy와 분리할 영속 리소스
Ansible bootstrap:
- scripts/ansible: kubeconfig 갱신, namespace, LimitRange, ArgoCD Helm install, 검증
Region: ap-south-1
VPC: 신규 생성
VPC CIDR: 10.0.0.0/16
Resource naming: AEGIS-[resource]-[feature]-[zone]
Target cluster name: AEGIS-EKS
Target Kubernetes version: 1.34
AZ: ap-south-1a, ap-south-1c
Subnets: public 2개 + private 2개
NAT Gateway: public Azone/Czone에 각 1개
Private route table: Azone/Czone 별도 구성
EKS endpoint: public endpoint
EKS endpoint CIDR: 0.0.0.0/0 (MVP bootstrap 임시 기준)
Node subnet: private subnet
Node group: EKS Managed Node Group
Instance type: t3.medium 기본
Node count: min/desired/max 2
Capacity: On-Demand
```

`t3.micro`는 사용하지 않는 기준이다. EKS system pod, CNI, CoreDNS, ArgoCD/Grafana/관측 컴포넌트까지 고려하면 메모리 여유가 작아 Hub MVP 기준선으로 부적합하다고 판단했다.

### M1 Issue 3 Hub ArgoCD

- 2026-05-04에 Hub EKS를 재생성했다.
- `infra/hub` Terraform apply 결과 `56 added, 0 changed, 0 destroyed`.
- `aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS` 완료.
- `kubectl get nodes -o wide`에서 EKS worker node 2대 `Ready` 확인.
- Hub namespace/LimitRange는 처음 Terraform으로 검증했고, 최종 기준은 Ansible bootstrap으로 전환했다.
- `argocd`, `observability`, `risk`, `ops-support` namespace `Active` 확인.
- 각 namespace에 `default-limits` LimitRange 생성 확인.
- ArgoCD Helm chart `argo/argo-cd` `9.5.11` 설치 완료.
- ArgoCD app version은 `v3.3.9`.
- Helm release는 `argocd`, namespace는 `argocd`.
- `/home/vicbear/Aegis/.tools/bin/argocd` CLI `v3.3.9` 설치 완료.
- `kubectl -n argocd port-forward service/argocd-server 8080:443`로 UI 접근을 검증했다.
- `https://127.0.0.1:8080` HTTP 200 확인.
- 초기 admin secret 생성 확인. 비밀번호 값은 문서에 기록하지 않는다.
- CLI admin login 성공.
- `argocd cluster list`에서 `https://kubernetes.default.svc` / `in-cluster` 확인.
- `argocd-server` service는 `ClusterIP` 유지. M1 Issue 3에서는 AWS LoadBalancer를 만들지 않았다.

## 현재 AWS 상태

```text
AWS 계정 연결: MFA 세션으로 확인 완료
AWS 리소스 생성: 현재 비활성
terraform destroy: infra/hub 완료
terraform state: infra/hub empty
EKS describe-cluster: AEGIS-EKS ResourceNotFoundException
```

주의:

- `terraform init`은 provider/module을 로컬에 내려받는 작업이라 AWS 리소스를 만들지 않는다.
- AWS 리소스가 실제로 만들어지는 시점은 `terraform apply` 실행 시점이다.
- 테스트가 끝나면 반드시 `terraform destroy`로 EKS, NAT Gateway, node group을 제거한다.
- 2026-05-04 현재 테스트 리소스는 제거 완료 상태다.

마지막 검증 후 제거된 주요 리소스:

```text
Cluster: AEGIS-EKS
Region: ap-south-1
Kubernetes version: 1.34
VPC: vpc-09ee4698847b2586d
Private subnets: subnet-0039656dbf579fb82, subnet-0f72d0e52ef0d0648
Public subnets: subnet-00eeeb6f502ecf887, subnet-075409b6b6dee6e96
Node group: AEGIS-EKS-node
Node status: 2 Ready
Hub namespaces: argocd, observability, risk, ops-support
Terraform apply: infra/hub 56 added
Ansible bootstrap: namespace, LimitRange, ArgoCD Helm release 재생성 기준 추가
Terraform destroy: infra/hub 56 destroyed
ArgoCD Helm release: argocd / argo-cd-9.5.11 / app v3.3.9
```

현재 Terraform 기준 이름:

```text
Cluster: AEGIS-EKS
Kubernetes version: 1.34
VPC name: AEGIS-VPC
Public subnets: AEGIS-Subnet-public-Azone, AEGIS-Subnet-public-Czone
Private subnets: AEGIS-Subnet-private-Azone, AEGIS-Subnet-private-Czone
NAT gateways: AEGIS-NAT-public-Azone, AEGIS-NAT-public-Czone
Private route tables: AEGIS-RouteTable-private-Azone, AEGIS-RouteTable-private-Czone
Node group: AEGIS-EKS-node
Cluster IAM role: AEGIS-IAMRole-EKS-cluster
Node IAM role: AEGIS-IAMRole-EKS-node
Cluster security group: AEGIS-SG-EKS
Node security group: AEGIS-SG-EKS-node
```

최신 확인:

```text
kubectl get nodes -o wide
2 Ready

kubectl get namespaces argocd observability risk ops-support
4 Active

kubectl -n argocd get pods
all Running / Ready

helm list -n argocd
argocd deployed argo-cd-9.5.11 app v3.3.9
```

2026-05-04 destroy 확인:

```text
infra/hub terraform state list
empty

aws eks describe-cluster --region ap-south-1 --name AEGIS-EKS
ResourceNotFoundException
```

## 다음에 할 일

### 1. 다음 Hub 재기동 순서

Hub EKS가 필요한 작업을 다시 시작할 때는 아래 순서로 올린다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
terraform plan -out=tfplan
terraform apply tfplan

aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS
```

Ansible bootstrap은 namespace, LimitRange, ArgoCD Helm release를 함께 재생성한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_bootstrap.yml
```

ArgoCD UI 접근:

```bash
/home/vicbear/Aegis/git_clone/Aegis-pi/scripts/hub/argocd-port-forward.sh
```

### 2. M1 Issue 4 S3 설계 및 Terraform 구성

다음 공식 이슈는 `M1 Issue 4 - [Hub/S3] 버킷 생성 및 경로 파티셔닝 설계`다.

작업 내용:

- S3 bucket 이름 결정
- public access block 적용
- versioning/encryption/lifecycle 기준 결정
- 경로 파티셔닝 규칙 확정: `{factory_id}/{source_type}/{yyyy}/{MM}/{dd}/`
- `infra/foundation`에 S3 Terraform 구성 추가
- 이후 IoT Core Rule이 적재할 prefix 기준 문서화

### 3. ArgoCD 접근 전략 유지

현재 ArgoCD 접근 기준:

- 지금은 사용자 로컬 PC에서 EKS kubeconfig를 설정한 뒤 `kubectl port-forward`로 접근한다.
- M2에서 Tailscale을 구성할 때 ArgoCD 접근 경로를 private access로 함께 정리한다.
- Tailscale 적용 후 EKS API endpoint public CIDR `0.0.0.0/0`를 축소한다.
- ArgoCD 설정은 UI 클릭보다 Git/YAML/ApplicationSet으로 코드화한다.
- ArgoCD public `LoadBalancer`는 만들지 않는다.

### 4. ArgoCD 재생성 자동화

EKS를 destroy/recreate할 때 ArgoCD 재설치를 반복하지 않도록 현재 수동 Helm install 기준을 Ansible bootstrap으로 전환했다.

적용 내용:

- `scripts/ansible/inventory/hub_eks_dynamic.sh` 추가 완료
- `scripts/ansible/inventory/group_vars/hub_eks.yml` 추가 완료
- `scripts/ansible/files/hub-bootstrap.yaml` 추가 완료
- `scripts/ansible/files/argocd-values.yaml` 추가 완료
- `scripts/ansible/playbooks/hub_argocd_bootstrap.yml` 추가 완료
- `scripts/ansible/playbooks/hub_argocd_verify.yml` 추가 완료
- `helm upgrade --install`로 `argo/argo-cd` chart `9.5.11` 관리
- release name `argocd`, namespace `argocd`, service type `ClusterIP` 유지
- repo, AppProject, Application, ApplicationSet은 후속 코드화
- 포트포워딩은 Terraform에 넣지 않고 `scripts/hub/argocd-port-forward.sh`로 제공
- dynamic inventory는 `infra/hub`의 `terraform output -json`을 읽어 cluster name, region, kubeconfig 명령을 Ansible 변수로 제공한다.
- 다음 `hub_argocd_bootstrap.yml` 실행 때 ArgoCD Helm release가 새로 생성된다.

포트포워딩 스크립트는 아래 흐름을 따른다.

```text
aws eks update-kubeconfig
kubectl -n argocd wait
kubectl -n argocd port-forward service/argocd-server 8080:443
```

### 5. 리소스 종료 기준

현재는 이미 제거 완료 상태다. 다음에 다시 올린 뒤 작업을 멈추거나 장시간 사용하지 않을 때는 비용 방지를 위해 아래 순서로 제거한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
terraform destroy
```

장시간 사용하지 않을 리소스를 남기지 않는다. EKS control plane, NAT Gateway, managed node group은 켜져 있는 동안 비용이 발생한다.

## 문서 갱신 상태

M1 Issue 3 Hub ArgoCD 설치, Ansible bootstrap 전환, destroy 완료 상태를 다음 문서에 반영했다.
또한 앞으로의 구현 책임 경계를 Terraform, Ansible, GitHub Actions, GitHub+ArgoCD 흐름으로 고정하고 관련 문서를 최신화했다.

- `README.md`
- `docs/README.md`
- `docs/issues/M1_hub-cloud.md`
- `docs/issues/M3_deploy-pipeline.md`
- `docs/issues/MASTER_CHECKLIST.md`
- `docs/issues/SESSION_STATE.md`
- `docs/ops/README.md`
- `docs/ops/13_hub_namespace_baseline.md`
- `docs/ops/14_hub_run_commands.md`
- `docs/planning/09_m1_eks_vpc_decision_record.md`
- `docs/planning/11_delivery_ownership_flow.md`
- `infra/README.md`
- `infra/hub/README.md`
- `infra/foundation/README.md`
- `scripts/README.md`
- `scripts/ansible/README.md`

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
M1 Issue 1 EKS/VPC Terraform apply 재실행 및 검증 완료
M1 Issue 2 namespace/LimitRange 검증 완료 및 Ansible bootstrap 전환 완료
M1 Issue 3 Hub ArgoCD Helm 설치 및 CLI/UI 검증 완료
M1 Issue 3 ArgoCD Helm release Ansible bootstrap 전환 완료
Hub/bootstrap 테스트 리소스 destroy 완료
infra/hub state empty
AWS AEGIS-EKS describe-cluster ResourceNotFoundException 확인
리소스 네이밍 규칙 AEGIS-[resource]-[feature]-[zone] 고정
Target EKS name AEGIS-EKS
Target Kubernetes version 1.34
EKS endpoint 0.0.0.0/0 MVP bootstrap 기준 유지
kubectl v1.34.7 로컬 설치
worker node 2대 Ready 확인
ArgoCD CLI v3.3.9 로컬 설치
책임 범위 분리 완료: infra/hub, scripts/ansible, infra/foundation
Delivery flow 확정: Terraform -> Ansible -> GitHub Actions CI -> GitHub/ArgoCD CD
```

## 갱신 규칙

- 이 파일은 새 내용을 아래에 계속 추가하지 않는다.
- 세션 저장 요청이 오면 `마일스톤 기준 진행 현황`, `현재 큰 상태`, `지금까지 완료한 일`, `현재 AWS 상태`, `다음에 할 일`, `현재 세션 정리 내용`을 현재 기준으로 갱신한다.
- 오래된 완료 기록이 현재 판단에 불필요하면 요약으로 줄인다.
- 공식 체크 여부는 항상 `docs/issues/MASTER_CHECKLIST.md`와 각 M0~M7 이슈 문서를 우선한다.
