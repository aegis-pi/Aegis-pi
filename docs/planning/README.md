# Planning Docs

이 디렉터리는 구현 전후의 설계 판단, 단계 계획, 의사결정 기록을 둔다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `00_project_overview.md` | 프로젝트 목적과 전체 확장 방향 |
| `01_safe_edge_transition.md` | 기존 Safe-Edge에서 Aegis-Pi로 확장하는 전환 기준 |
| `02_implementation_plan.md` | 단계별 구현 계획 |
| `03_evaluation_plan.md` | 평가와 검증 계획 |
| `04_document_creation_priority.md` | 문서 작성 우선순위 |
| `05_decision_rationale.md` | 주요 기술 선택의 이유와 대안 검토 |
| `06_edge_agent_deployment_plan.md` | Edge Agent 구현과 K3s 배포 계획 |
| `07_dashboard_vpc_extension_plan.md` | Dashboard VPC 기반 관리자 관제 구조 |
| `08_aws_cli_mfa_terraform_access.md` | AWS CLI MFA와 Terraform 접근 준비 |
| `09_m1_eks_vpc_decision_record.md` | M1 EKS/VPC 설계 결정과 적용 결과 |

## 기준

- 실제 적용된 결정은 가능한 한 Decision Record 형태로 남긴다.
- 운영 절차로 확정된 내용은 `docs/ops/` 문서로 옮겨 실행 기준을 분리한다.
