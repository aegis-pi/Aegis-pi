# M1 Issue 1 EKS/VPC 설계 결정 기록

상태: source of truth
기준일: 2026-04-30

## 목적

M1 Hub 클라우드 기반 구성의 첫 번째 구현 단위인 EKS/VPC 기준값을 확정한다. 이 문서는 Terraform skeleton의 입력 기준이며, 실제 인프라 생성 전 설계 판단을 고정하기 위한 Decision Record다.

## 범위

이 결정은 Hub Processing VPC와 EKS 클러스터의 MVP 기준, 2026-04-30 적용/검증 결과, 그리고 최소 Terraform root 분리 기준을 다룬다.

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
| Resource naming | `AEGIS-[resource]-[feature]-[zone]` | AWS 콘솔과 Terraform state에서 리소스 역할을 즉시 구분하기 위한 공통 규칙이다. `feature`와 `zone`은 필요한 경우에만 사용한다. |
| Kubernetes version | `1.34` | Hub EKS 목표 버전은 1.34로 고정한다. 실제 적용 전에는 AWS/EKS 지원 여부와 add-on 호환성을 `terraform plan`으로 확인한다. |
| VPC | 신규 VPC를 Terraform으로 생성 | 기존 VPC 의존성을 제거하고, subnet/tag/NAT/EKS discovery tag를 코드로 재현 가능하게 만든다. MVP에서 환경을 다시 만들거나 지울 때도 추적이 쉽다. |
| VPC CIDR | `10.0.0.0/16` | Hub Processing VPC 기본 대역으로 고정한다. 후속 Dashboard VPC나 Spoke CIDR과는 별도 대역으로 관리한다. |
| AZ 수 | 2개 AZ: `ap-south-1a`, `ap-south-1c` | 단일 AZ보다 장애 격리가 낫고, 3개 AZ보다 subnet 수가 적다. Bzone 대신 A/Czone 기준으로 고정한다. |
| Subnet | public 2개 + private 2개 | public subnet은 ALB/NAT gateway 같은 외부 진입 리소스에 사용하고, private subnet은 EKS nodegroup을 배치해 워커 노드 직접 노출을 피한다. |
| NAT Gateway | AZ별 NAT Gateway 2개 | private node의 image pull, AWS API 접근을 위해 NAT가 필요하다. private Azone은 public Azone NAT, private Czone은 public Czone NAT를 사용하도록 route table도 AZ별로 분리한다. |
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
| Terraform modules | EKS는 `terraform-aws-modules/eks/aws` `21.14.0`, VPC는 직접 AWS 리소스 | VPC/subnet/NAT/route table은 A/C zone별 라우팅 요구가 단순하고 명확해 직접 리소스로 관리한다. EKS는 관리 복잡도가 높아 검증된 module을 사용한다. |
| Terraform backend | 초기 skeleton은 local backend | backend용 S3/DynamoDB를 아직 만들기 전이므로 local backend로 시작한다. Hub bootstrap 후 remote state backend로 전환한다. |
| Responsibility split | `infra/hub`, `scripts/ansible`, `infra/foundation` | EKS 자체는 Terraform, 클러스터 bootstrap은 Ansible, 영속 데이터 리소스는 별도 Terraform root로 분리한다. |

## 리소스 이름 기준

이후 AWS 리소스 이름은 아래 형식으로 고정한다.

```text
AEGIS-[resource]-[feature]-[zone]
```

현재 Terraform 목표 이름:

| 기존 이름 | 변경 기준 이름 |
| --- | --- |
| `aegis-pi-hub-mvp-vpc` | `AEGIS-VPC` |
| `aegis-pi-hub-mvp-vpc-public-ap-south-1a` | `AEGIS-Subnet-public-Azone` |
| `aegis-pi-hub-mvp-vpc-public-ap-south-1c` | `AEGIS-Subnet-public-Czone` |
| `aegis-pi-hub-mvp-vpc-private-ap-south-1a` | `AEGIS-Subnet-private-Azone` |
| `aegis-pi-hub-mvp-vpc-private-ap-south-1c` | `AEGIS-Subnet-private-Czone` |
| 단일 NAT Gateway | `AEGIS-NAT-public-Azone`, `AEGIS-NAT-public-Czone` |
| 단일 private route table | `AEGIS-RouteTable-private-Azone`, `AEGIS-RouteTable-private-Czone` |
| `aegis-pi-hub-mvp` | `AEGIS-EKS` |
| `aegis-pi-hub-mvp-nodes` | `AEGIS-EKS-node` |
| `aegis-pi-hub-mvp-cluster-*` | `AEGIS-IAMRole-EKS-cluster` |
| `aegis-pi-hub-mvp-nodes-eks-node-group-*` | `AEGIS-IAMRole-EKS-node` |
| `hub-*` launch template | `AEGIS-LT-EKS-node` |
| `aegis-pi-hub-mvp-cluster` security group | `AEGIS-SG-EKS` |
| `aegis-pi-hub-mvp-node` security group | `AEGIS-SG-EKS-node` |

EKS cluster name과 node group name은 이름 변경 시 교체가 발생한다. 2026-04-30에는 기존 `aegis-pi-hub-mvp` 인프라를 `terraform destroy`로 제거한 뒤, 이 네이밍 규칙과 Kubernetes `1.34` 기준으로 새로 생성했다. 이후 namespace/LimitRange까지 검증한 뒤 비용 절감을 위해 다시 destroy했다.

## Terraform 파일 구조

최소 책임 분리 기준은 다음 구조를 따른다.

```text
infra/hub         VPC, subnet, NAT Gateway, EKS cluster, node group
scripts/ansible   kubeconfig, namespace, LimitRange, ArgoCD bootstrap
infra/foundation  S3, ECR, AMP, IoT Core처럼 EKS destroy와 분리할 영속 리소스
```

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
| `main.tf` | VPC/subnet/NAT/route table 직접 리소스와 EKS module 호출 |
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
aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS
kubectl get nodes
kubectl cluster-info
```

5. Hub Kubernetes bootstrap 적용

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_bootstrap.yml
```

6. 테스트 후 인프라 제거

MVP Hub 인프라는 EKS control plane, NAT Gateway, managed node group 비용이 지속 발생한다. 테스트가 끝나면 반드시 제거한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
terraform destroy
```

## 적용 결과

2026-04-30에 기존 인프라를 제거한 뒤 `infra/hub` Terraform root에서 `terraform apply`를 다시 실행했다. 이후 namespace와 LimitRange를 검증했고, 2026-05-04에는 최종 bootstrap 기준을 Ansible로 전환했다.

결과:

```text
infra/hub apply: 56 added, 0 changed, 0 destroyed.
final destroy: 56 destroyed.
```

생성 후 삭제한 주요 리소스:

| 항목 | 값 |
| --- | --- |
| Cluster | `AEGIS-EKS` |
| Region | `ap-south-1` |
| Kubernetes API status | `ACTIVE` |
| Kubernetes version | `1.34` |
| VPC | `vpc-099138d8d344bda9b` |
| Private subnets | `subnet-0f08c63b578cd815b`, `subnet-0f6536a1d45d25594` |
| Public subnets | `subnet-02bcb3ab6a4768128`, `subnet-02f443deece3d6bbf` |
| Node group | `AEGIS-EKS-node` |
| Node instance type | `t3.medium` |
| Node count | desired/min/max `2` |
| Hub namespaces | `argocd`, `observability`, `risk`, `ops-support` |
| Current AWS status | destroyed |
| Current Terraform state | empty |
| Empty-state hub plan | `56 to add, 0 to change, 0 to destroy` |

검증:

```text
kubectl get nodes
```

두 worker node가 모두 `Ready` 상태로 확인됐다.

```text
kubectl cluster-info
```

EKS control plane과 CoreDNS endpoint 응답을 확인했다.

최종 destroy 후 확인:

```text
terraform state list
empty

aws eks describe-cluster --region ap-south-1 --name AEGIS-EKS
ResourceNotFoundException
```

## 완료 기준 매핑

| M1 Issue 1 완료 조건 | 현재 반영 |
| --- | --- |
| 리전 결정 | `ap-south-1` 확정 |
| VPC/서브넷 사용 방식 결정 | 신규 VPC, 2 AZ, public/private 각 2개 확정 |
| EKS API endpoint 공개 범위 결정 | public endpoint + MVP bootstrap `0.0.0.0/0` 허용 확정 |
| EKS 클러스터 생성 | `AEGIS-EKS` 생성 및 `ACTIVE` 확인 |
| 노드그룹 구성 | managed node group, On-Demand `t3.medium` 2대 생성 및 `Ready` 확인 |
| `kubectl` 로컬 접근 설정 | `aws eks update-kubeconfig` 수행 및 `kubectl get nodes` 확인 |
| EKS Add-on 설치 | `vpc-cni`, `coredns`, `kube-proxy` 생성 확인 |
| IAM OIDC Provider 연결 | EKS module로 OIDC provider 생성 완료 |

## 후속 검토 항목

- EKS endpoint private access를 VPN/Tailscale/Bastion 준비 이후 활성화할지 검토한다.
- EKS public endpoint CIDR을 `0.0.0.0/0`에서 고정 작업자 CIDR 또는 private endpoint 중심으로 좁힌다.
- nodegroup instance type을 `t3.medium`에서 `t3.large`로 올릴 필요가 있는지 실제 pod resource 사용량으로 판단한다.
- 비용 절감이 필요하면 `t3.micro`보다 node count 조정, 테스트 후 즉시 `terraform destroy`, 또는 후속 Spot 혼합을 우선 검토한다.
- Terraform remote backend용 S3/DynamoDB bootstrap을 별도 issue로 분리할지 결정한다.

## 참고

- Terraform Registry `terraform-aws-modules/eks/aws`: `21.14.0`
