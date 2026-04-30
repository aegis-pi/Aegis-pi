# Hub Infrastructure

이 디렉터리는 EKS, S3, IoT Core, AMP 등 Hub 쪽 클라우드 인프라 정의 파일을 둔다.

후속 확장에서는 관리자 대시보드용 Dashboard VPC도 함께 설계한다.

Dashboard VPC는 Processing VPC와 VPC Peering 없이 Route53, ALB, WAF, Auth, Dashboard Web/API를 제공하고, processed S3와 latest status store를 read-only IAM으로 조회한다.

기준 문서:

```text
docs/planning/07_dashboard_vpc_extension_plan.md
docs/planning/08_aws_cli_mfa_terraform_access.md
```

Terraform으로 이 디렉터리의 AWS 리소스를 만들기 전에는 `docs/planning/08_aws_cli_mfa_terraform_access.md` 기준으로 MFA 기반 AWS CLI 세션을 먼저 검증한다.
