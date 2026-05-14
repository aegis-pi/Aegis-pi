# Hub Infrastructure

이 디렉터리는 Hub EKS를 실행하기 위한 AWS 네트워크와 클러스터 기준선을 관리한다.

현재 MVP 구성은 M1 Issue 1의 VPC/EKS 기준선이다. EKS OIDC에 묶인 IRSA IAM Role/Policy, Route53 Hosted Zone, ACM certificate는 Terraform으로 관리하고, Kubernetes namespace, LimitRange, ArgoCD, Prometheus Agent, Grafana, AWS Load Balancer Controller, ServiceAccount annotation, Admin Ingress 같은 클러스터 bootstrap 리소스는 `scripts/ansible`의 Hub bootstrap playbook에서 관리한다.

전체 책임 경계는 `docs/planning/11_delivery_ownership_flow.md`를 따른다. 이 디렉터리는 Terraform 기반 AWS 인프라만 담당한다.

후속 확장에서는 사용자 대시보드와 데이터 처리용 1번 Data / Dashboard VPC도 함께 설계한다.

Data / Dashboard VPC는 Control / Management VPC와 상시 private service 호출 없이 Route53, ALB, WAF, Auth, Dashboard Web/API를 제공하고, DynamoDB LATEST/HISTORY와 S3 processed를 조회한다.

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
├── admin_ui_dns.tf
├── aws_load_balancer_controller_iam_policy.json
├── irsa_aws_load_balancer_controller.tf
├── irsa_grafana_amp_query.tf
├── irsa_prometheus_remote_write.tf
├── irsa_risk_normalizer.tf
├── outputs.tf
└── terraform.tfvars.example
```

최소 분리 기준:

```text
infra/hub         Control / Management VPC, subnet, NAT Gateway, EKS cluster, node group, Route53/ACM, EKS-bound IRSA IAM roles
scripts/ansible   kubeconfig, Kubernetes namespace, LimitRange, ArgoCD bootstrap, AWS Load Balancer Controller, Admin Ingress, ServiceAccount annotation
infra/foundation  S3, AMP, IoT Core처럼 EKS destroy와 분리할 영속 리소스. ECR은 M3 이미지 파이프라인 단계에서 추가 예정
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

## 태그 전파 기준

Hub Terraform은 provider `default_tags`와 EKS module `tags`에 동일한 공통 태그를 명시해 Terraform이 직접 생성하는 리소스와 EKS module 하위 리소스가 같은 비용 추적 기준을 갖도록 한다.

```text
Project     = AEGIS
Environment = hub-mvp
ManagedBy   = terraform
Component   = hub
```

EKS Managed Node Group이 간접 생성하는 EC2 instance, EBS volume, network interface는 launch template `tag_specifications`로 공통 태그를 전파한다. 비용 조회는 `Project=AEGIS` 태그와 `Name=AEGIS-EKS-node`를 함께 확인한다. EKS가 관리하는 Auto Scaling Group 자체는 직접 비용이 붙는 리소스가 아니며, 실제 비용 계산은 EKS control plane, EC2 node, EBS, NAT Gateway, Public IPv4 기준으로 한다.

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
| IRSA role | `AEGIS-IAMRole-IRSA-risk-normalizer` | - | `risk/risk-normalizer` S3 access |
| IRSA role | `AEGIS-IAMRole-IRSA-prometheus-remote-write` | - | `observability/prometheus-agent` AMP remote_write |
| IRSA role | `AEGIS-IAMRole-IRSA-grafana-amp-query` | - | `observability/grafana` AMP query |
| IRSA role | `AEGIS-IAMRole-IRSA-aws-load-balancer-controller` | - | `kube-system/aws-load-balancer-controller` ALB management |
| Route53 hosted zone | `minsoo-tech.cloud` | - | Admin UI DNS delegation |
| ACM certificate | `minsoo-tech.cloud` + Admin UI SANs | `ap-south-1` | ALB HTTPS certificate |

## Hub Bootstrap 기준

Issue 2~3/7~10 기준 Hub namespace, ArgoCD, Prometheus Agent, Grafana, AWS Load Balancer Controller, Admin Ingress는 Ansible local bootstrap으로 관리한다. Ansible은 EC2 SSH가 아니라 로컬/CI에서 EKS Kubernetes API에 접근한다.

| Namespace | 역할 | 관리 위치 |
| --- | --- | --- |
| `argocd` | Hub에서 Spoke 배포 제어 | `scripts/ansible/files/hub-bootstrap.yaml` |
| `observability` | Grafana, AMP 연동 메트릭 관제 | `scripts/ansible/files/hub-bootstrap.yaml` |
| `risk` | M1 Hub 배포/IRSA 검증용 또는 임시 risk workload. 최신 MVP에서는 별도 Risk 계산 파드를 두지 않음 | `scripts/ansible/files/hub-bootstrap.yaml` |
| `ops-support` | M1 보조 namespace. 최신 목표에서는 `pipeline_status` 갱신을 Lambda data processor가 담당 | `scripts/ansible/files/hub-bootstrap.yaml` |

M1 검증용 `risk/risk-normalizer`, `observability/prometheus-agent`, `observability/grafana`, `kube-system/aws-load-balancer-controller` ServiceAccount는 Hub bootstrap playbook이 생성하거나 확인하고 Terraform output의 IRSA role ARN으로 annotation한다.

M1 검증용 risk-normalizer IRSA 권한 범위:

```text
role: AEGIS-IAMRole-IRSA-risk-normalizer
service account: risk/risk-normalizer
raw/factory-a/*: read only
processed/*: write
latest/factory-a/*: write
delete: not allowed
raw write: not allowed
```

검증 결과:

```text
assumed role: arn:aws:sts::611058323802:assumed-role/AEGIS-IAMRole-IRSA-risk-normalizer/botocore-session-1778033798
raw read: s3://aegis-bucket-data/raw/factory-a/
latest write: s3://aegis-bucket-data/latest/factory-a/irsa-test.json
raw write denied: s3://aegis-bucket-data/raw/factory-a/irsa-denied.txt
```

Prometheus remote_write IRSA 권한 범위:

```text
role: AEGIS-IAMRole-IRSA-prometheus-remote-write
service account: observability/prometheus-agent
workspace: arn:aws:aps:ap-south-1:611058323802:workspace/ws-6a8853dc-0eb4-43e7-9b97-efade5b75765
allowed action: aps:RemoteWrite
```

검증 결과:

```text
assumed role: arn:aws:sts::611058323802:assumed-role/AEGIS-IAMRole-IRSA-prometheus-remote-write/botocore-session-1778037092
remote_write endpoint: https://aps-workspaces.ap-south-1.amazonaws.com/workspaces/ws-6a8853dc-0eb4-43e7-9b97-efade5b75765/api/v1/remote_write
```

검증:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_verify.yml
```

## 현재 AWS 상태

2026-05-08 기준 Hub 인프라는 검증 후 비용 정리를 위해 `scripts/destroy/destroy-all.sh`로 삭제했다. `AEGIS-EKS`, `AEGIS-VPC`, node group, NAT Gateway, Admin UI ALB, Route53 Hosted Zone, ACM certificate, Hub IRSA IAM Role/Policy는 삭제 확인했다. EKS encryption용 AEGIS KMS key는 AWS KMS 삭제 대기 정책에 따라 `PendingDeletion` 상태로 남는다.

| 항목 | 값 |
| --- | --- |
| Terraform state | destroy 완료 |
| Cluster | deleted (`AEGIS-EKS`) |
| Kubernetes version | `1.34` |
| VPC | deleted |
| Public subnets | deleted |
| Private subnets | deleted |
| Node group | deleted (`AEGIS-EKS-node`) |
| Hub namespaces | deleted with EKS |
| ArgoCD | deleted with EKS |
| IRSA role | deleted (`AEGIS-IAMRole-IRSA-risk-normalizer`) |
| Prometheus remote_write IRSA role | deleted (`AEGIS-IAMRole-IRSA-prometheus-remote-write`) |
| Grafana AMP query IRSA role | deleted (`AEGIS-IAMRole-IRSA-grafana-amp-query`) |
| AWS Load Balancer Controller | deleted with EKS |
| Admin UI Route53 zone | deleted (`minsoo-tech.cloud`) |
| Admin UI ACM certificate | deleted |
| Admin UI ALB | deleted |

재생성 후 검증:

```bash
aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS
kubectl get nodes
kubectl cluster-info
kubectl -n argocd get pods
kubectl -n kube-system get deploy aws-load-balancer-controller
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
