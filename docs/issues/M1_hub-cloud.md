# M1. Hub 클라우드 기반 구성

> **마일스톤 목표**: EKS 클러스터와 AWS 관리형 서비스(IoT Core, S3, AMP), Dashboard VPC 기준을 구성한다.
> 이 단계에서는 Spoke 연결 없이 Hub 자체를 세우는 것이 목표다.  
> M0(`factory-a` 기준선) 완료 후 진행하며, M2(Mesh VPN 연결)의 전제 조건이다.
> 관리자 대시보드 접근 구조는 `docs/planning/07_dashboard_vpc_extension_plan.md`를 따른다.
> AWS CLI MFA 및 Terraform 접근 준비는 `docs/planning/08_aws_cli_mfa_terraform_access.md`를 따른다.
> EKS/VPC MVP 설계 결정은 `docs/planning/09_m1_eks_vpc_decision_record.md`를 따른다.

---

## 수정 이력

| 날짜 | 버전 | 내용 |
| --- | --- | --- |
| 2026-05-04 | rev-20260504-01 | Issue 3 Hub ArgoCD 설치 완료 결과, 접근 운영 기준, Terraform 편입 계획을 반영 |
| 2026-05-04 | rev-20260504-02 | ArgoCD Helm release를 `infra/platform` Terraform 관리 대상으로 편입하고 포트포워딩 스크립트 기준을 반영 |
| 2026-05-04 | rev-20260504-03 | Hub/Platform destroy 완료 상태와 재적용 시 ArgoCD 자동 재생성 기준을 반영 |
| 2026-05-04 | rev-20260504-04 | ArgoCD와 Hub namespace 재생성을 Terraform에서 Ansible dynamic inventory 기반 bootstrap으로 전환 |
| 2026-05-04 | rev-20260504-05 | Terraform, Ansible, GitHub Actions, GitHub+ArgoCD 책임 경계 기준을 반영 |
| 2026-05-04 | rev-20260504-06 | Issue 4 S3 데이터 버킷을 `infra/foundation` Terraform root에 추가하고 raw/processed/latest prefix 및 lifecycle 기준을 반영 |
| 2026-05-04 | rev-20260504-07 | `aegis-bucket-data` S3 버킷 apply 및 versioning, SSE-S3, public access block, lifecycle 검증 결과를 반영 |
| 2026-05-04 | rev-20260504-08 | Hub EKS/ArgoCD 재생성 및 `factory-a` IoT Thing/Policy/K3s Secret 생성 결과를 현재 상태로 반영 |
| 2026-05-04 | rev-20260504-09 | 전체 destroy 완료 후 Hub/Foundation/IoT/K3s Secret 삭제 상태를 현재 기준으로 반영 |

---

## Issue 0 - [AWS/Auth] AWS CLI MFA 및 Terraform 접근 설정

### 목표 (What & Why)

M1 Hub 인프라를 Terraform으로 생성하기 전에 로컬 터미널에서 AWS CLI와 Terraform이 MFA 기반 STS 임시 세션으로 동작하도록 준비한다.

이 이슈는 새 IAM 사용자 생성을 포함하지 않는다. 이미 준비된 IAM 사용자, Access Key, 권한, MFA 장치를 사용한다.

### 완료 조건 (Definition of Done)

- [x] 기존 IAM Access Key / Secret Access Key를 `aws configure`로 등록
- [x] MFA device ARN 확인
- [x] `aws-mfa-script` 설치 및 `mfa.cfg` 구성
- [x] `.bashrc`에 Aegis AWS 환경 로더 등록
- [x] `mfa <OTP>` 실행 후 STS 임시 환경 변수 설정 확인
- [x] `aws sts get-caller-identity`로 대상 AWS 계정 확인
- [x] `terraform init` 및 인증 오류 없는 `terraform plan` 확인
- [x] Access Key, Secret Key, Session Token, MFA OTP를 문서와 Git에 기록하지 않음

### Acceptance Criteria

- `AWS_SESSION_TOKEN`이 설정된 동일 shell에서 AWS CLI 명령이 동작한다.
- Terraform provider가 하드코딩된 credential 없이 현재 shell의 MFA 세션을 사용한다.
- 인증 실패와 권한 부족을 구분해 설명할 수 있다.

### 완료 기록

- 완료일: 2026-04-30
- 기본 리전: `ap-south-1`
- 로컬 도구 경로: `/home/vicbear/Aegis/.tools`
- 세부 절차: `docs/planning/08_aws_cli_mfa_terraform_access.md`

---

## Issue 1 - [Hub/EKS] 클러스터 생성 및 기본 설정

### 목표 (What & Why)

Aegis-Pi Hub의 실행 환경인 EKS 클러스터를 생성한다.  
ArgoCD, Grafana, Risk Score Engine 등 모든 Hub 컴포넌트가 EKS 위에서 동작하기 때문에  
클러스터 구성이 Hub 전체의 기반이 된다.

### 완료 조건 (Definition of Done)

- [x] Issue 0의 AWS CLI MFA 및 Terraform 접근 설정 완료
- [x] 리전, VPC/서브넷 사용 방식, EKS API endpoint 공개 범위 결정
- [x] EKS 클러스터 생성 (리전 결정 및 적용)
- [x] 노드그룹 구성 (인스턴스 타입, 최소/최대 노드 수 설정)
- [x] `kubectl` 로컬 접근 설정 (`kubeconfig` 업데이트)
- [x] EKS Add-on 설치
  - `vpc-cni`
  - `coredns`
  - `kube-proxy`
- [x] IAM OIDC Provider 연결 (IRSA 사용을 위한 전제)

### Acceptance Criteria

- `kubectl get nodes`에서 노드그룹 노드 `Ready` 상태 확인
- `kubectl cluster-info`에서 EKS API 엔드포인트 확인
- 로컬 환경에서 `kubectl` 명령 정상 동작

### 설계 결정 기록

- 문서: `docs/planning/09_m1_eks_vpc_decision_record.md`
- Delivery ownership: `docs/planning/11_delivery_ownership_flow.md`
- Region: `ap-south-1`
- VPC: Terraform 신규 생성
- VPC CIDR: `10.0.0.0/16`
- Subnet: `ap-south-1a`, `ap-south-1c`에 public 2개 + private 2개
- NAT Gateway: public Azone/Czone에 각 1개, private route table도 Azone/Czone 별도 구성
- Resource naming: `AEGIS-[resource]-[feature]-[zone]`
- Target cluster name: `AEGIS-EKS`
- Target Kubernetes version: `1.34`
- EKS nodegroup: private subnet, On-Demand, `t3.medium` 기본, 2대
- EKS API endpoint: MVP bootstrap 단계에서는 public endpoint + `0.0.0.0/0` 허용
- 테스트 종료 시 `terraform destroy`로 EKS, NAT Gateway, node group을 반드시 제거

### 완료 기록

- 완료일: 2026-04-30
- 최신 확인일: 2026-05-04
- Terraform apply 결과: `infra/hub 56 added, 0 changed, 0 destroyed`
- Cluster: `AEGIS-EKS`
- Region: `ap-south-1`
- Kubernetes API: `ACTIVE`, Kubernetes `1.34`
- VPC: `vpc-0f5ce54353ff2e3ac`
- Private subnets: `subnet-0a9bb5682ea4025d5`, `subnet-0a28852262f757477`
- Public subnets: `subnet-0e7cb5c97552bb8cd`, `subnet-0754802aef5b374e2`
- Node group: `AEGIS-EKS-node`, `t3.medium`, desired/min/max `2`
- `kubectl get nodes` 확인: worker node 2대 모두 `Ready`
- `kubectl cluster-info` 확인: control plane 및 CoreDNS endpoint 응답 정상
- 최소 분리 구조: `infra/hub`는 VPC/EKS, `scripts/ansible`은 namespace/LimitRange/ArgoCD bootstrap, `infra/foundation`은 S3/ECR/AMP/IoT Core 같은 영속 리소스
- 이후 모든 신규 작업은 Terraform = 인프라, Ansible = bootstrap/설정/소프트웨어, GitHub Actions = CI, GitHub+ArgoCD = CD 기준으로 분류한다.
- 현재 `infra/hub` state는 active이며, Hub EKS와 ArgoCD가 올라와 있다.

---

## Issue 2 - [Hub/Kubernetes] 네임스페이스 설계 및 생성

### 🎯 목표 (What & Why)

EKS 내부 기능을 역할 기준으로 분리하여 관리한다.  
네임스페이스 경계가 명확해야 이후 ArgoCD ApplicationSet 배포 대상, Grafana 데이터 소스 구분,  
Risk Score Engine 독립 운영이 가능하다.

### ✅ 완료 조건 (Definition of Done)

- [x] 아래 네임스페이스 생성 및 역할 정의 문서화
  - `argocd` - Hub에서 Spoke 배포 제어
  - `observability` - Grafana, AMP 연동 메트릭 관제
  - `risk` - Risk Score Engine, 정규화 서비스
  - `ops-support` - `pipeline_status` 집계 보조 기능
- [x] 각 네임스페이스에 기본 ResourceQuota 또는 LimitRange 설정 (선택)
- [x] 네임스페이스 구조를 `docs/architecture/00_current_architecture.md` 또는 Hub 운영 문서에 반영

### 🔍 Acceptance Criteria

- `kubectl get namespaces`에서 4개 네임스페이스 확인
- 각 네임스페이스 역할이 문서에 명시되어 있음

### 구현 기록

- 관리 파일: `scripts/ansible/files/hub-bootstrap.yaml`
- 관리 방식: Ansible local bootstrap + `kubectl apply`
- Namespace 역할 문서: `infra/hub/README.md`, `docs/ops/13_hub_namespace_baseline.md`
- Terraform apply 결과: `infra/hub 56 added, 0 changed, 0 destroyed`
- `kubectl get namespaces argocd observability risk ops-support` 확인: 4개 namespace 모두 `Active`
- `kubectl get limitrange` 확인: 각 namespace에 `default-limits` 생성 완료
- namespace 관리는 Terraform이 아니라 Ansible bootstrap으로 전환했다.
- 현재 AWS에는 Hub EKS와 namespace가 없다. destroy/recreate 이후에는 `scripts/build/build-hub.sh`가 Terraform apply와 Ansible bootstrap을 순서대로 수행한다.

---

## Issue 3 - [Hub/ArgoCD] ArgoCD 설치 (Spoke 등록 전 단계)

### 🎯 목표 (What & Why)

Hub의 중앙 배포 제어 계층인 ArgoCD를 EKS에 설치한다.  
이 단계에서는 Spoke 클러스터 등록은 하지 않는다. (M2에서 Mesh VPN 연결 후 진행)  
ArgoCD 자체가 정상 동작하는 상태까지만 완료한다.

### ✅ 완료 조건 (Definition of Done)

- [x] `argocd` 네임스페이스에 ArgoCD 설치
- [x] ArgoCD 초기 admin 비밀번호 확인
- [x] ArgoCD UI 접근 가능 확인 (LoadBalancer 또는 포트포워딩)
- [x] ArgoCD CLI 로컬 설정 완료
- [x] ArgoCD 버전 및 설치 방식 관련 문서에 기록

### 🔍 Acceptance Criteria

- ArgoCD UI 브라우저 접근 가능
- `argocd cluster list`에서 in-cluster(EKS 자체) 확인
- Spoke 등록 없이도 ArgoCD 자체 `Healthy` 상태

### 구현 기록

- 완료일: 2026-05-04
- 설치 방식: Helm chart `argo/argo-cd`
- Helm release: `argocd`
- Namespace: `argocd`
- Chart version: `argo-cd-9.5.11`
- ArgoCD app version: `v3.3.9`
- ArgoCD CLI: `/home/vicbear/Aegis/.tools/bin/argocd`, `v3.3.9`
- UI 접근 방식: `kubectl -n argocd port-forward service/argocd-server 8080:443`
- UI 검증: `https://127.0.0.1:8080` HTTP 200 확인
- Service 노출: `argocd-server`는 `ClusterIP` 유지. M1 Issue 3에서는 AWS LoadBalancer를 만들지 않았다.
- 초기 admin secret: `argocd-initial-admin-secret` 생성 확인. 비밀번호 값은 문서에 기록하지 않는다.
- CLI 검증: admin login 성공, `argocd cluster list`에서 `https://kubernetes.default.svc` / `in-cluster` 확인.
- Pod 검증: `argocd-application-controller`, `argocd-applicationset-controller`, `argocd-dex-server`, `argocd-notifications-controller`, `argocd-redis`, `argocd-repo-server`, `argocd-server` 모두 `Running` / `Ready` 확인.

### 운영 기준

- 현재 단계의 ArgoCD UI 접근은 사용자 로컬 PC에서 EKS kubeconfig를 설정한 뒤 `kubectl port-forward`로 수행한다.
- `argocd-server`는 `ClusterIP`로 유지한다.
- M1 단계에서는 ArgoCD public `LoadBalancer`를 만들지 않는다.
- UI는 상태 확인, diff 확인, 수동 sync 검증 용도로 사용한다.
- repo, Project, Application, ApplicationSet처럼 반복 적용해야 하는 설정은 UI 클릭에만 의존하지 않고 Git/YAML/ApplicationSet으로 코드화한다.
- M2에서 Tailscale을 구성할 때 ArgoCD 접근 경로를 private access로 전환한다.
- Tailscale 적용 후 EKS API endpoint public CIDR `0.0.0.0/0`를 더 좁힌다.

### Ansible bootstrap 기준

ArgoCD는 수동 Helm install과 Terraform Helm release 편입을 검증한 뒤, 최종 운영 기준을 Ansible local bootstrap으로 전환했다. 이후 EKS를 destroy/recreate할 때는 `infra/hub terraform apply` 후 Ansible playbook이 namespace, LimitRange, ArgoCD Helm release를 재생성한다.

구성:

- `scripts/ansible/inventory/hub_eks_dynamic.sh` 추가 완료
- `scripts/ansible/inventory/group_vars/hub_eks.yml` 추가 완료
- `scripts/ansible/files/hub-bootstrap.yaml` 추가 완료
- `scripts/ansible/files/argocd-values.yaml` 추가 완료
- `scripts/ansible/playbooks/hub_argocd_bootstrap.yml` 추가 완료
- `scripts/ansible/playbooks/hub_argocd_verify.yml` 추가 완료
- `helm upgrade --install`로 `argo/argo-cd` chart `9.5.11` 관리
- release name `argocd`, namespace `argocd` 유지
- `argocd-server` service type `ClusterIP` 명시
- repo, AppProject, Application, ApplicationSet은 후속으로 코드화

Ansible inventory는 EC2 node SSH 대상이 아니라 `localhost` 대상이다. `infra/hub`의 `terraform output -json`에서 `cluster_name`, `aws_region`, `update_kubeconfig_command`를 읽어 EKS Kubernetes API에 접근한다.

포트포워딩은 Ansible 설치 대상에 넣지 않는다. 장기 실행 로컬 프로세스이므로 `scripts/ops/argocd-port-forward.sh` 운영 스크립트로 제공한다.

### 현재 실행 상태

2026-05-04 전체 destroy 이후 Hub EKS와 ArgoCD는 삭제된 상태다.

결과:

- `infra/hub`: `56 destroyed`
- `infra/hub` Terraform state: empty
- Hub EKS/VPC/node group/NAT Gateway: deleted
- ArgoCD/Hub namespace: EKS destroy와 함께 deleted
- `infra/foundation`: `6 destroyed`
- S3 bucket `aegis-bucket-data`: deleted

이후 다시 올릴 때는 아래 단일 진입점을 사용하면 Terraform apply와 Ansible bootstrap이 순서대로 실행된다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
```

---

## Issue 4 - [Hub/S3] 버킷 생성 및 경로 파티셔닝 설계

### 🎯 목표 (What & Why)

Edge에서 올라온 데이터를 장기 보존하는 중앙 원본 적재 지점을 구성한다.  
공장/source_type/날짜 기준 파티셔닝으로 이후 정규화 서비스가 데이터를 효율적으로 읽을 수 있게 한다.

### ✅ 완료 조건 (Definition of Done)

- [x] S3 버킷 생성 (버킷 이름, 리전, 퍼블릭 액세스 차단 설정)
- [x] 경로 파티셔닝 규칙 확정 및 Terraform 코드 반영
  - raw: `raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json`
  - processed: `processed/{dataset}/{factory_id}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json`
  - latest: `latest/{factory_id}/status.json`, `latest/{factory_id}/risk-score.json`
- [ ] IoT Rule → S3 적재 연결 확인 (Issue 5와 연계)
- [ ] S3 버킷 정책 및 IAM Role 설정 (EKS 서비스 계정 접근 허용)
- [x] 파티셔닝 규칙을 foundation 문서에 반영

### Terraform 기준

- Root: `infra/foundation`
- Bucket: `aegis-bucket-data`
- Region: `ap-south-1`
- Versioning: enabled
- Encryption: SSE-S3 (`AES256`)
- Public access block: enabled
- Lifecycle:
  - `raw/`: 90일 후 Glacier Instant Retrieval 전환
  - `processed/`: 365일 후 Standard-IA 전환
  - `latest/`: current object 삭제 없음, noncurrent version 30일 후 삭제
  - 전체 incomplete multipart upload 7일 후 중단

Public access block은 다른 VPC 접근을 막기 위한 설정이 아니라 인터넷 공개를 차단하는 안전장치다. 다른 VPC, EKS, EC2에서 접근해야 할 때는 IAM Role, S3 VPC Endpoint, bucket policy로 허용한다.

### 완료 기록

- 완료일: 2026-05-04
- Terraform apply 결과: `6 added, 0 changed, 0 destroyed`
- Terraform state:
  - `aws_s3_bucket.data`
  - `aws_s3_bucket_lifecycle_configuration.data`
  - `aws_s3_bucket_ownership_controls.data`
  - `aws_s3_bucket_public_access_block.data`
  - `aws_s3_bucket_server_side_encryption_configuration.data`
  - `aws_s3_bucket_versioning.data`
- AWS API 검증:
  - versioning `Enabled`
  - public access block 4개 옵션 모두 `true`
  - server-side encryption `AES256`
  - lifecycle rule 4개 적용 확인

### 🔍 Acceptance Criteria

- IoT Core 테스트 메시지 발행 후 S3 지정 경로에 파일 적재 확인
- EKS 내부 파드에서 S3 버킷 접근 가능 (IRSA 기반)
- 잘못된 경로에 데이터가 적재되지 않음

---

## Issue 5 - [Hub/IoT Core] Thing / 인증서 / 규칙 구성

### 🎯 목표 (What & Why)

각 Spoke의 Edge Agent가 데이터를 전송할 IoT Core 진입점을 구성한다.  
Thing, 인증서, 정책, IoT Rule을 설정하여 Edge → IoT Core → S3 파이프라인의 앞단을 완성한다.

### ✅ 완료 조건 (Definition of Done)

- [x] IoT Core Thing 생성 (공장별 Thing 또는 통합 Thing 방식 결정 및 적용)
- [x] X.509 인증서 생성 및 Thing 연결
- [x] IoT 정책 생성 (`iot:Connect`, `iot:Publish`, `iot:Subscribe` 권한)
- [ ] IoT Rule 생성 (수신 메시지 → S3 적재 연결)
- [x] IoT Core 엔드포인트 확인 및 기록
- [ ] 테스트 메시지 발행 및 IoT Core 수신 확인

### 🔍 Acceptance Criteria

- AWS 콘솔 IoT Core `MQTT 테스트 클라이언트`에서 테스트 메시지 수신 확인
- IoT Rule이 트리거되어 S3에 메시지 적재 확인 (Issue 4 이후)
- 인증서 파일이 안전하게 보관됨 (Edge Agent 배포 시 사용)

### 현재 기록

- Thing: `AEGIS-IoTThing-factory-a`
- Policy: `AEGIS-IoTPolicy-factory-a`
- Topic prefix: `aegis/factory-a`
- Local secret path: `secret/iot/factory-a/`
- K3s Secret: `ai-apps/aws-iot-factory-a-cert`
- 다음 작업: IoT Rule -> S3 `raw/` prefix 적재 연결

---

## Issue 6 - [관제/AMP] AMP(Amazon Managed Prometheus) Workspace 생성 및 접근 권한 준비

### 🎯 목표 (What & Why)

각 Spoke 메트릭의 중앙 수집 대상이 되는 AMP Workspace를 먼저 준비한다.  
이 이슈에서는 Workspace 생성과 쓰기 권한 준비까지 완료하고, 실제 메트릭 전송은 다음 이슈에서 수행한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] AMP Workspace 생성
- [ ] IAM Role 및 IRSA 설정 (Prometheus → AMP 쓰기 권한)
- [ ] AMP Workspace ARN 및 엔드포인트 기록
- [ ] AMP 접근 정책을 Hub 관제 관련 문서에 반영

### 🔍 Acceptance Criteria

- AWS 콘솔에서 AMP Workspace 생성 확인
- Prometheus 서비스 계정에 연결할 IAM/IRSA 구성이 준비됨
- AMP Workspace ARN 및 remote_write 엔드포인트를 참조 가능

---

## Issue 6A - [관제/Dashboard VPC] 외부 관리자 접근 VPC 설계

### 🎯 목표 (What & Why)

관리자가 Tailscale 없이 접근할 수 있는 대시보드 접근 영역을 설계한다.

Dashboard VPC는 Processing VPC와 VPC Peering/TGW로 연결하지 않고, processed S3와 latest status store를 read-only IAM으로 조회한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Dashboard VPC CIDR, public/private subnet, route table 설계
- [ ] Route53, ALB, WAF, Cognito/Auth 사용 방식 결정
- [ ] Dashboard Web/API 배치 방식 결정
- [ ] Processing VPC와 직접 네트워크 연결하지 않는 원칙 문서화
- [ ] Dashboard API IAM read-only 정책 범위 정의
  - processed S3 prefix read
  - latest status store read
  - raw bucket full access 금지
  - EKS/ArgoCD/Spoke API 접근 금지

### 🔍 Acceptance Criteria

- Dashboard VPC 설계가 `docs/planning/07_dashboard_vpc_extension_plan.md`와 일치
- 관리자 접근 경로가 Route53 -> ALB -> WAF/Auth -> Dashboard API로 설명 가능
- Dashboard API가 읽을 저장소와 권한 범위가 문서화됨

---

## Issue 7 - [관제/Prometheus] Hub Prometheus 설치 및 AMP remote_write 구성

### 🎯 목표 (What & Why)

Hub EKS 내부에서 메트릭을 수집할 Prometheus(또는 Agent)를 설치하고 AMP로 전송한다.  
이 단계가 완료되어야 내부 관측용 Grafana 또는 후속 Dashboard API가 AMP/metrics 계층을 참조할 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `observability` 네임스페이스에 Prometheus 또는 Prometheus Agent 설치
- [ ] EKS 기본 메트릭 수집 대상 확인
  - 노드/파드/클러스터 기본 메트릭
- [ ] AMP remote_write 설정 적용
- [ ] IRSA 기반으로 AMP 쓰기 권한 연결
- [ ] 메트릭 수신 여부 확인 및 설정 기록

### 🔍 Acceptance Criteria

- Prometheus(또는 Agent) 파드 `Running`
- AMP 콘솔 또는 쿼리로 메트릭 수신 확인
- remote_write 오류 없이 지속 수집되는 로그 확인

---

## Issue 8 - [관제/Grafana] 내부 관측용 Grafana/AMP 데이터 소스 기준 결정

### 🎯 목표 (What & Why)

Hub 내부 관측에 사용할 Grafana 또는 AMP 조회 기준을 구성한다.

본사 관리자용 외부 대시보드는 Dashboard VPC의 Web/API로 확장하며, Grafana를 그대로 public 관리자 화면으로 노출하지 않는다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `observability` 네임스페이스에 Grafana 설치 여부 결정
- [ ] Grafana를 설치하는 경우 초기 admin 비밀번호 설정
- [ ] Grafana 접근 방식을 내부 운영용으로 제한할지 결정
- [ ] 데이터 소스 연결
  - AMP (Prometheus 호환)
- [ ] Grafana 버전 및 설치 방식 기록
- [ ] Dashboard VPC가 조회할 latest status store 후보를 문서에 명시

### 🔍 Acceptance Criteria

- Grafana를 설치하는 경우 UI 접근 가능
- AMP 데이터 소스 `Test` 버튼 성공
- Explore 탭에서 AMP 기본 메트릭 쿼리 결과 확인
- 외부 관리자 대시보드와 내부 Grafana의 역할 차이가 문서화됨

---

## Issue 9 - [Risk/Config] `runtime-config.yaml` 파일 구조 초안 작성

### 🎯 목표 (What & Why)

Hub 단에서 공장별 필드 사용 여부와 Risk 가중치를 제어하는 중앙 설정 파일 구조를 확정한다.  
이 구조가 M6(Risk Twin)에서 실제 가중치 계산의 기반이 되며,  
공장별 override 구조도 이 파일에서 관리된다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `configs/runtime/runtime-config.yaml` 경로 생성
- [ ] 전역(`global`) 섹션 구조 정의
  - 필드별 `display` / `risk_enabled` 불리언
  - 필드별 가중치 초기값
- [ ] 공장별(`factories`) override 섹션 구조 정의
  - `factory_id` 기준 override 키
  - 초기에는 구조만 준비, 실제 값은 전역 설정 사용
- [ ] 구조 예시 작성 (아래 참고)

```yaml
global:
  fields:
    temperature:
      display: true
      risk_enabled: true
      weight: 15
    humidity:
      display: true
      risk_enabled: true
      weight: 10
    node_status:
      display: true
      risk_enabled: true
      weight: 20
    # ... 전체 필드 목록

factories:
  factory-a:
    fields: {}      # 현재는 전역 설정 사용
  factory-b:
    fields: {}
  factory-c:
    fields: {}
```

- [ ] 구조를 구성 관리 관련 문서에 반영

### 🔍 Acceptance Criteria

- `configs/runtime/runtime-config.yaml` 파일이 존재하고 유효한 YAML 형식
- `global` / `factories` 섹션 구조 확인
- Risk Score 가중치 합산이 100 이하임을 문서에 명시
