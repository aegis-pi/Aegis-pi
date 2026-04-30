# M1 Issue 1 EKS/VPC 설계 결정 기록

상태: source of truth
기준일: 2026-04-30

## 목적

M1 Hub 클라우드 기반 구성의 첫 번째 구현 단위인 EKS/VPC 기준값을 확정한다. 이 문서는 Terraform skeleton의 입력 기준이며, 실제 인프라 생성 전 설계 판단을 고정하기 위한 Decision Record다.

## 범위

이 결정은 Hub Processing VPC와 EKS 클러스터의 MVP 기준만 다룬다.

포함:

- AWS 리전
- VPC 생성 방식
- AZ 및 subnet 구조
- EKS node 배치 위치
- EKS API endpoint 공개 범위
- Managed node group 기본값
- Terraform 모듈 사용 기준

제외:

- Dashboard VPC 상세 구현
- S3/IoT Core/AMP 상세 리소스
- Tailscale Hub-Spoke 연결
- ArgoCD 설치

## 결정 사항

| 항목 | 결정 | MVP 근거 |
| --- | --- | --- |
| Region | `ap-south-1` | 사용자 AWS 작업 리전으로 확정했다. 이후 S3, IoT Core, EKS, AMP를 같은 리전에 두면 MVP 단계에서 cross-region 비용과 지연을 줄일 수 있다. |
| VPC | 신규 VPC를 Terraform으로 생성 | 기존 VPC 의존성을 제거하고, subnet/tag/NAT/EKS discovery tag를 코드로 재현 가능하게 만든다. MVP에서 환경을 다시 만들거나 지울 때도 추적이 쉽다. |
| VPC CIDR | `10.40.0.0/16` | Safe-Edge 로컬망 `10.10.10.0/24`와 충돌하지 않는 별도 대역이다. 후속 Dashboard VPC나 Spoke CIDR과도 분리해 관리하기 쉽다. |
| AZ 수 | 2개 AZ | 단일 AZ보다 장애 격리가 낫고, 3개 AZ보다 비용과 subnet 수가 적다. MVP에서 가용성과 단순성의 균형이 좋다. |
| Subnet | public 2개 + private 2개 | public subnet은 ALB/NAT gateway 같은 외부 진입 리소스에 사용하고, private subnet은 EKS nodegroup을 배치해 워커 노드 직접 노출을 피한다. |
| NAT Gateway | 단일 NAT Gateway | private node의 image pull, AWS API 접근을 위해 NAT가 필요하다. MVP에서는 AZ별 NAT보다 비용을 줄이기 위해 단일 NAT로 시작한다. 운영 단계에서는 AZ별 NAT로 확장 검토한다. |
| EKS node placement | private subnet | 워커 노드에 public IP를 붙이지 않고, 외부 접근면을 EKS API와 필요한 ingress 계층으로 제한한다. |
| EKS API endpoint | public endpoint 활성화 + MVP bootstrap 단계에서는 `0.0.0.0/0` 허용 | 현재 로컬 작업자가 이동하면서 Terraform/kubectl로 접근해야 하므로 작업자 public IP `/32` 고정은 불편하다. 초기 MVP에서는 IAM/MFA 인증을 전제로 `0.0.0.0/0`를 허용하되, 운영 전에는 VPN/Tailscale/Bastion 또는 고정 작업자 CIDR로 좁힌다. |
| EKS private endpoint | 비활성으로 시작 | private endpoint는 VPN/Direct Connect/Bastion 경로가 준비된 뒤 효과가 크다. MVP에서는 초기 접근성과 디버깅을 우선한다. |
| Node group | EKS Managed Node Group | AWS 관리형 노드 생명주기를 사용해 직접 ASG/Launch Template 관리 부담을 줄인다. |
| Instance type | `t3.medium` 기본, 필요 시 `t3.large` | MVP 제어/관측 컴포넌트 실행은 `t3.medium`으로 시작한다. ArgoCD/Grafana/Risk Engine 리소스가 부족하면 `t3.large`로 올린다. |
| `t3.micro` 사용 여부 | 사용하지 않음 | `t3.micro`는 메모리가 작아 EKS 기본 system pod, CNI, CoreDNS를 올린 뒤 ArgoCD/Grafana/관측 컴포넌트를 안정적으로 수용하기 어렵다. 단순 생성 실험은 가능하지만 Hub MVP 기준선으로는 장애 분석 변수를 늘린다. |
| Node count | min/desired/max 모두 2 | 2개 AZ에 기본 분산하고, MVP 비용 예측을 단순하게 유지한다. 자동 확장은 후속 단계에서 Cluster Autoscaler 또는 Karpenter 도입 시 재검토한다. |
| Capacity type | On-Demand | MVP 인프라 기준선 검증에서는 Spot 회수 이벤트를 변수로 넣지 않는다. 안정화 뒤 비용 최적화 단계에서 Spot 혼합을 검토한다. |
| EKS add-ons | `vpc-cni`, `coredns`, `kube-proxy` | M1 Issue 1 완료 조건에 포함된 기본 add-on이다. EKS module의 managed add-on으로 시작해 버전 관리를 AWS/EKS 기준에 맞춘다. |
| IRSA/OIDC | 활성화 | 후속 S3, AMP, IoT 연동에서 Pod 단위 IAM 권한 분리가 필요하다. M1 단계에서 OIDC provider를 미리 연결한다. |
| Cluster admin | cluster creator admin 권한 활성화 | 초기 Terraform 작업자가 `kubectl`로 클러스터를 검증해야 하므로 생성자 admin 권한을 부여한다. 운영 단계에서는 별도 IAM role 기반 접근으로 좁힌다. |
| Terraform modules | `terraform-aws-modules/vpc/aws` `6.6.1`, `terraform-aws-modules/eks/aws` `21.14.0` | Terraform Registry 기준 최신 계열을 명시적으로 pinning한다. 모듈 업그레이드는 별도 변경 기록으로 관리한다. |
| Terraform backend | 초기 skeleton은 local backend | backend용 S3/DynamoDB를 아직 만들기 전이므로 local backend로 시작한다. Hub bootstrap 후 remote state backend로 전환한다. |

## Terraform 파일 구조

`infra/hub/`의 MVP skeleton은 다음 구조를 따른다.

```text
infra/hub/
├── README.md
├── .terraform.lock.hcl
├── versions.tf
├── providers.tf
├── locals.tf
├── variables.tf
├── main.tf
├── outputs.tf
└── terraform.tfvars.example
```

역할:

| 파일 | 역할 |
| --- | --- |
| `versions.tf` | Terraform 및 provider/module 버전 기준 |
| `.terraform.lock.hcl` | Terraform provider version lock |
| `providers.tf` | AWS provider 리전 설정 |
| `locals.tf` | 공통 이름, 태그, subnet CIDR 계산 |
| `variables.tf` | 외부에서 바꿀 입력값 정의 |
| `main.tf` | VPC/EKS module 호출 |
| `outputs.tf` | kubeconfig와 후속 모듈에서 필요한 출력 |
| `terraform.tfvars.example` | 실제 적용 전 복사해서 채울 예시값 |

## 적용 순서

1. MFA 세션 발급

```bash
source ~/.bashrc
mfa <OTP>
unset AWS_PROFILE
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION=ap-south-1
```

2. Terraform 입력값 준비

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
cp terraform.tfvars.example terraform.tfvars
```

MVP bootstrap 단계에서는 `cluster_endpoint_public_access_cidrs = ["0.0.0.0/0"]`로 시작한다. 이 값은 이동 작업 편의를 위한 임시 기준이며, 운영 전에는 반드시 좁힌다.

3. Terraform 검증

```bash
terraform fmt -recursive
terraform init
terraform validate
terraform plan
```

4. 생성 후 kubeconfig 연결

```bash
aws eks update-kubeconfig --region ap-south-1 --name aegis-pi-hub-mvp
kubectl get nodes
kubectl cluster-info
```

5. 테스트 후 인프라 제거

MVP Hub 인프라는 EKS control plane, NAT Gateway, managed node group 비용이 지속 발생한다. 테스트가 끝나면 반드시 제거한다.

```bash
terraform destroy
```

## 완료 기준 매핑

| M1 Issue 1 완료 조건 | 현재 반영 |
| --- | --- |
| 리전 결정 | `ap-south-1` 확정 |
| VPC/서브넷 사용 방식 결정 | 신규 VPC, 2 AZ, public/private 각 2개 확정 |
| EKS API endpoint 공개 범위 결정 | public endpoint + MVP bootstrap `0.0.0.0/0` 허용 확정 |
| EKS 클러스터 생성 | Terraform skeleton 준비, apply 전 |
| 노드그룹 구성 | managed node group, On-Demand 2대 기준 확정 |
| `kubectl` 로컬 접근 설정 | apply 후 `aws eks update-kubeconfig`로 수행 예정 |
| EKS Add-on 설치 | `vpc-cni`, `coredns`, `kube-proxy` module에 반영 |
| IAM OIDC Provider 연결 | EKS module 기준 활성화 |

## 후속 검토 항목

- 운영 전환 시 NAT Gateway를 AZ별로 둘지 결정한다.
- EKS endpoint private access를 VPN/Tailscale/Bastion 준비 이후 활성화할지 검토한다.
- EKS public endpoint CIDR을 `0.0.0.0/0`에서 고정 작업자 CIDR 또는 private endpoint 중심으로 좁힌다.
- nodegroup instance type을 `t3.medium`에서 `t3.large`로 올릴 필요가 있는지 실제 pod resource 사용량으로 판단한다.
- 비용 절감이 필요하면 `t3.micro`보다 node count 조정, 테스트 후 즉시 `terraform destroy`, 또는 후속 Spot 혼합을 우선 검토한다.
- Terraform remote backend용 S3/DynamoDB bootstrap을 별도 issue로 분리할지 결정한다.

## 참고

- Terraform Registry `terraform-aws-modules/vpc/aws`: `6.6.1`
- Terraform Registry `terraform-aws-modules/eks/aws`: `21.14.0`
