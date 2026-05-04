# Hub Infrastructure

이 디렉터리는 Hub EKS를 실행하기 위한 AWS 네트워크와 클러스터 기준선을 관리한다.

현재 MVP 구성은 M1 Issue 1의 VPC/EKS 기준선이다. Kubernetes namespace, LimitRange, ArgoCD 같은 클러스터 bootstrap 리소스는 Terraform이 아니라 `scripts/ansible`의 Hub bootstrap playbook에서 관리한다.

전체 책임 경계는 `docs/planning/11_delivery_ownership_flow.md`를 따른다. 이 디렉터리는 Terraform 기반 AWS 인프라만 담당한다.

후속 확장에서는 관리자 대시보드용 Dashboard VPC도 함께 설계한다.

Dashboard VPC는 Processing VPC와 VPC Peering 없이 Route53, ALB, WAF, Auth, Dashboard Web/API를 제공하고, processed S3와 latest status store를 read-only IAM으로 조회한다.

기준 문서:

```text
docs/planning/07_dashboard_vpc_extension_plan.md
docs/planning/08_aws_cli_mfa_terraform_access.md
docs/planning/09_m1_eks_vpc_decision_record.md
```

Terraform으로 이 디렉터리의 AWS 리소스를 만들기 전에는 `docs/planning/08_aws_cli_mfa_terraform_access.md` 기준으로 MFA 기반 AWS CLI 세션을 먼저 검증한다.

## Terraform 파일 구조

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

최소 분리 기준:

```text
infra/hub         VPC, subnet, NAT Gateway, EKS cluster, node group
scripts/ansible   kubeconfig, Kubernetes namespace, LimitRange, ArgoCD bootstrap
infra/foundation  S3, ECR, AMP, IoT Core처럼 EKS destroy와 분리할 영속 리소스
```

## MVP 기본값

| 항목 | 값 |
| --- | --- |
| Region | `ap-south-1` |
| VPC | 신규 생성 |
| VPC CIDR | `10.0.0.0/16` |
| AZ | 2개: `ap-south-1a`, `ap-south-1c` |
| Subnets | public 2개 + private 2개 |
| NAT Gateway | AZ별 1개, 총 2개 |
| Resource naming | `AEGIS-[resource]-[feature]-[zone]` |
| EKS cluster name | `AEGIS-EKS` |
| Kubernetes version | `1.34` |
| EKS node subnet | private subnet |
| EKS endpoint | public endpoint + `0.0.0.0/0` MVP bootstrap 허용 |
| Node group | EKS Managed Node Group |
| Instance type | `t3.medium` 기본, 필요 시 `t3.large` |
| Node count | min/desired/max `2` |
| Capacity | On-Demand |

`t3.micro`는 EKS system pod와 Hub 기본 컴포넌트에 비해 메모리 여유가 작아 MVP 기준선에서는 사용하지 않는다. 비용 절감은 테스트 후 즉시 `terraform destroy`하는 방식으로 우선 관리한다.

## 네이밍 규칙

AWS 리소스 이름은 아래 규칙을 따른다.

```text
AEGIS-[resource]-[feature]-[zone]
```

- `resource`: `VPC`, `Subnet`, `EKS`, `SG`, `IAMRole`, `LT`, `NAT`, `IGW`, `RouteTable`처럼 AWS 리소스 종류를 쓴다.
- `feature`: `private`, `public`, `cluster`, `node`처럼 역할 구분이 필요할 때만 쓴다.
- `zone`: AZ 구분이 필요한 리소스에 `Azone`, `Bzone`, `Czone` 형식으로 붙인다.

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

네이밍 규칙과 Kubernetes `1.34` 변경을 반영하기 위해 기존 `aegis-pi-hub-mvp` 인프라는 2026-04-30에 `terraform destroy`로 제거했고, 같은 날 새 기준으로 다시 생성했다.

## 다음 적용 목표

현재 Terraform 기준으로 다시 적용하면 VPC는 `10.0.0.0/16`, AZ는 `ap-south-1a`와 `ap-south-1c`로 구성된다. private subnet은 각 AZ의 NAT Gateway를 바라보는 별도 route table에 연결된다.

| 리소스 | 이름 | AZ | CIDR/역할 |
| --- | --- | --- | --- |
| VPC | `AEGIS-VPC` | - | `10.0.0.0/16` |
| Public subnet | `AEGIS-Subnet-public-Azone` | `ap-south-1a` | `10.0.0.0/24` |
| Public subnet | `AEGIS-Subnet-public-Czone` | `ap-south-1c` | `10.0.1.0/24` |
| Private subnet | `AEGIS-Subnet-private-Azone` | `ap-south-1a` | `10.0.10.0/24` |
| Private subnet | `AEGIS-Subnet-private-Czone` | `ap-south-1c` | `10.0.11.0/24` |
| NAT Gateway | `AEGIS-NAT-public-Azone` | `ap-south-1a` | private Azone egress |
| NAT Gateway | `AEGIS-NAT-public-Czone` | `ap-south-1c` | private Czone egress |
| Public route table | `AEGIS-RouteTable-public` | - | IGW route |
| Private route table | `AEGIS-RouteTable-private-Azone` | `ap-south-1a` | NAT Azone route |
| Private route table | `AEGIS-RouteTable-private-Czone` | `ap-south-1c` | NAT Czone route |
| EKS cluster | `AEGIS-EKS` | - | Kubernetes `1.34` |
| EKS node group | `AEGIS-EKS-node` | private A/C | `t3.medium`, desired `2` |

## Hub Bootstrap 기준

Issue 2~3 기준 Hub namespace와 ArgoCD는 Ansible local bootstrap으로 관리한다. Ansible은 EC2 SSH가 아니라 로컬/CI에서 EKS Kubernetes API에 접근한다.

| Namespace | 역할 | 관리 위치 |
| --- | --- | --- |
| `argocd` | Hub에서 Spoke 배포 제어 | `scripts/ansible/files/hub-bootstrap.yaml` |
| `observability` | Grafana, AMP 연동 메트릭 관제 | `scripts/ansible/files/hub-bootstrap.yaml` |
| `risk` | Risk Score Engine, 정규화 서비스 | `scripts/ansible/files/hub-bootstrap.yaml` |
| `ops-support` | `pipeline_status` 집계 보조 기능 | `scripts/ansible/files/hub-bootstrap.yaml` |

검증:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_verify.yml
```

## 현재 AWS 상태

2026-04-30 기준 테스트로 올렸던 Hub 인프라는 최소 분리 작업 전에 다시 `terraform destroy`로 제거했다.

| 항목 | 값 |
| --- | --- |
| Destroy result | `infra/hub 56 destroyed`, bootstrap 리소스는 EKS와 함께 제거 |
| Terraform state | empty |
| AWS EKS describe-cluster | `ResourceNotFoundException` |
| Cluster | 삭제됨 |
| Kubernetes version | `1.34` |
| VPC | 삭제됨 |
| Node group | 삭제됨 |
| Hub namespaces | 삭제됨 |

검증:

```bash
aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS
kubectl get nodes
kubectl cluster-info
```

`kubectl`은 프로젝트 로컬 도구 경로 `/home/vicbear/Aegis/.tools/bin/kubectl`에 `v1.34.7`로 설치했다.

## 실행 순서

```bash
source ~/.bashrc
mfa <OTP>
unset AWS_PROFILE
export AWS_REGION=ap-south-1
export AWS_DEFAULT_REGION=ap-south-1

cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
cp terraform.tfvars.example terraform.tfvars
```

MVP bootstrap 단계에서는 이동 작업 편의를 위해 `cluster_endpoint_public_access_cidrs = ["0.0.0.0/0"]`로 시작한다. IAM/MFA 인증은 여전히 필요하지만, EKS API endpoint 네트워크 접근면은 넓어진다. 운영 전에는 VPN/Tailscale/Bastion 또는 고정 작업자 CIDR 기준으로 좁힌다.

```bash
terraform fmt -recursive
terraform init
terraform validate
terraform plan
```

`terraform apply` 후 Ansible bootstrap을 실행한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_bootstrap.yml
```

## 테스트 후 정리 원칙

MVP Hub 인프라는 비용이 지속 발생한다. EKS control plane, NAT Gateway, managed node group은 테스트가 끝나면 반드시 제거한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
terraform destroy
```

장시간 사용하지 않을 인프라를 남겨두지 않는다. `terraform apply`는 실험 시작, `terraform destroy`는 실험 종료 절차로 함께 기록한다. ArgoCD와 namespace는 EKS 내부 리소스라 EKS destroy와 함께 제거된다.
