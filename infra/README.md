# Infrastructure

이 디렉터리는 Aegis-Pi 인프라 구성을 영역별로 나누어 둔다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `hub/` | AWS Hub Processing VPC, subnet, NAT Gateway, EKS, node group Terraform 구성 |
| `foundation/` | S3, ECR, AMP, IoT Core처럼 EKS destroy와 분리할 영속 리소스 자리 |
| `safe-edge/` | `factory-a` Safe-Edge 기준선 복구 관련 인프라 문서 |
| `mesh-vpn/` | Tailscale 기반 Hub-Spoke 제어망 구성 문서 |
| `deploy/` | 배포 파이프라인 관련 인프라와 보조 설정 |

## 기준

- Terraform state, tfvars, provider cache는 Git에 커밋하지 않는다.
- AWS 리소스를 생성하기 전 `docs/planning/08_aws_cli_mfa_terraform_access.md`의 MFA 세션 기준을 따른다.
- 인프라는 Terraform으로만 관리한다. 클러스터 위 설정/소프트웨어는 Ansible, 배포 CI/CD는 GitHub Actions와 ArgoCD 기준을 따른다.
- Hub 재생성은 `infra/hub` Terraform apply 후 `scripts/ansible/playbooks/hub_argocd_bootstrap.yml` 순서로 진행한다.
- 삭제는 EKS 내부 bootstrap 리소스를 별도 destroy하지 않고 `infra/hub` Terraform destroy로 클러스터와 함께 제거한다.
