# Infrastructure

이 디렉터리는 Aegis-Pi 인프라 구성을 영역별로 나누어 둔다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `foundation/` | S3, ECR, DynamoDB처럼 Hub EKS destroy와 분리되는 영속 리소스 Terraform 구성. Hub를 내려도 유지한다 |
| `data-pipeline/` | IoT Rule × 3 (factory-a/b/c), Lambda DataProcessor, IAM. on-demand 레이어. `build-data-pipe.sh` / `destroy-data-pipe.sh`로 개별 관리 |
| `reporting/` | Bedrock 기반 daily factory report Scheduler, Step Functions, Lambda, IAM/Logs. on-demand 레이어. `build-reporting.sh` / `destroy-reporting.sh`로 개별 관리 |
| `hub/` | Control / Management VPC, subnet, 단일 NAT Gateway, EKS, node group Terraform 구성 |
| `safe-edge/` | `factory-a` Safe-Edge 기준선 복구 관련 인프라 문서 |
| `mesh-vpn/` | Tailscale 기반 Hub-Spoke 제어망 구성 문서 |
| `deploy/` | 배포 파이프라인 관련 인프라와 보조 설정 |

## 기준

- Terraform state, tfvars, provider cache는 Git에 커밋하지 않는다.
- AWS 리소스를 생성하기 전 `docs/planning/08_aws_cli_mfa_terraform_access.md`의 MFA 세션 기준을 따른다.
- 인프라는 Terraform으로만 관리한다. 클러스터 위 설정/소프트웨어는 Ansible, 배포 CI/CD는 GitHub Actions와 ArgoCD 기준을 따른다.
- Hub 재생성은 `infra/hub` Terraform apply 후 `scripts/ansible/playbooks/hub_argocd_bootstrap.yml`, `hub_prometheus_agent_cleanup.yml`, `hub_grafana_bootstrap.yml` 순서로 진행한다.
- Hub 삭제는 EKS 내부 bootstrap 리소스를 별도 destroy하지 않고 `infra/hub` Terraform destroy로 클러스터와 함께 제거한다.
- 전체 삭제는 `scripts/destroy/destroy-all.sh`를 사용한다. 기본 동작은 data-pipeline → Hub 순서이며, IoT/Foundation은 명시적 플래그(`DESTROY_IOT=true`, `DESTROY_FOUNDATION=true`)를 지정해야 삭제한다.
- `infra/data-pipeline` destroy는 `infra/foundation` destroy 이전에 반드시 먼저 수행해야 한다. data-pipeline이 foundation의 DynamoDB를 data source로 참조하기 때문이다.
- `infra/reporting` destroy도 `infra/foundation` destroy 이전에 먼저 수행한다. reporting은 foundation S3 bucket을 data source로 참조한다.
