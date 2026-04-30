# Hub Infrastructure

이 디렉터리는 EKS, S3, IoT Core, AMP 등 Hub 쪽 클라우드 인프라 정의 파일을 둔다.

현재 MVP skeleton은 M1 Issue 1의 EKS/VPC 기준선을 구성한다.

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

## MVP 기본값

| 항목 | 값 |
| --- | --- |
| Region | `ap-south-1` |
| VPC | 신규 생성 |
| VPC CIDR | `10.40.0.0/16` |
| AZ | 2개 |
| Subnets | public 2개 + private 2개 |
| EKS node subnet | private subnet |
| EKS endpoint | public endpoint + `0.0.0.0/0` MVP bootstrap 허용 |
| Node group | EKS Managed Node Group |
| Instance type | `t3.medium` 기본, 필요 시 `t3.large` |
| Node count | min/desired/max `2` |
| Capacity | On-Demand |

`t3.micro`는 EKS system pod와 Hub 기본 컴포넌트에 비해 메모리 여유가 작아 MVP 기준선에서는 사용하지 않는다. 비용 절감은 테스트 후 즉시 `terraform destroy`하는 방식으로 우선 관리한다.

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

`terraform apply` 후 kubeconfig를 갱신한다.

```bash
aws eks update-kubeconfig --region ap-south-1 --name aegis-pi-hub-mvp
kubectl get nodes
kubectl cluster-info
```

## 테스트 후 정리 원칙

MVP Hub 인프라는 비용이 지속 발생한다. EKS control plane, NAT Gateway, managed node group은 테스트가 끝나면 반드시 제거한다.

```bash
terraform destroy
```

장시간 사용하지 않을 인프라를 남겨두지 않는다. `terraform apply`는 실험 시작, `terraform destroy`는 실험 종료 절차로 함께 기록한다.
