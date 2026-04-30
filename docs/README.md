# Aegis-Pi Docs

상태: source of truth
기준일: 2026-04-29

## 목적

이 디렉터리는 Aegis-Pi 프로젝트의 설계, 운영, 검증, 시연, 보고 문서를 관리한다.

## 현재 상태

- 현재 완료된 구현 범위는 `factory-a` Safe-Edge 기준선이다.
- `factory-a`는 Raspberry Pi 3-node K3s 기반 운영형 Spoke다.
- 2026-04-29 기준 AI snapshot은 node-local hostPath를 사용하며, AI 추론 결과는 InfluxDB PVC를 통해 Longhorn에 저장한다.
- 2026-04-29 기준 LAN 제거 및 `k3s-agent` 중지 failover/failback 재검증을 완료했다.
- AWS Hub, `factory-b`, `factory-c`, IoT Core, S3, ECR, GitHub Actions, Tailscale은 후속 단계다.
- 현재 운영 source of truth는 `docs/ops/` 문서다.
- 마일스톤 추적은 `docs/issues/` 문서를 따른다.
- 계획과 실제 구현이 달라진 결정은 `docs/changes/`에서 추적한다.
- 후속 관리자 대시보드는 `planning/07_dashboard_vpc_extension_plan.md`의 Dashboard VPC 방향을 따른다.
- AWS CLI MFA 및 Terraform 접근 준비는 `planning/08_aws_cli_mfa_terraform_access.md`를 따른다.

## 먼저 읽을 문서

1. `ops/05_factory_a_status.md`
2. `ops/00_quick_start.md`
3. `ops/01_safe_edge_bootstrap.md`
4. `ops/06_argocd_gitops.md`
5. `ops/07_grafana_dashboard.md`
6. `ops/08_data_retention.md`
7. `ops/09_failover_failback_test_results.md`
8. `ops/10_edge_workload_placement.md`
9. `ops/11_ansible_test_automation.md`
10. `changes/README.md`
11. `planning/06_edge_agent_deployment_plan.md`
12. `planning/07_dashboard_vpc_extension_plan.md`
13. `planning/08_aws_cli_mfa_terraform_access.md`
14. `issues/M0_factory-a_safe-edge-baseline.md`

## 문서 구조

```text
docs/
├── README.md
├── issues/
│   ├── MASTER_CHECKLIST.md
│   ├── M0_factory-a_safe-edge-baseline.md
│   └── M1~M7...
├── changes/
│   ├── README.md
│   └── 0001~...
├── ops/
│   ├── 00_quick_start.md
│   ├── 01_safe_edge_bootstrap.md
│   ├── 02_self_check.md
│   ├── 03_test_checklist.md
│   ├── 04_troubleshooting.md
│   ├── 05_factory_a_status.md
│   ├── 06_argocd_gitops.md
│   ├── 07_grafana_dashboard.md
│   ├── 08_data_retention.md
│   ├── 09_failover_failback_test_results.md
│   ├── 10_edge_workload_placement.md
│   └── 11_ansible_test_automation.md
├── architecture/
├── planning/
│   ├── 00_project_overview.md
│   ├── 01_safe_edge_transition.md
│   ├── 02_implementation_plan.md
│   ├── 03_evaluation_plan.md
│   ├── 04_document_creation_priority.md
│   ├── 05_decision_rationale.md
│   ├── 06_edge_agent_deployment_plan.md
│   ├── 07_dashboard_vpc_extension_plan.md
│   └── 08_aws_cli_mfa_terraform_access.md
├── product/
├── specs/
├── demo/
├── presentation/
└── report/
```

## 현재 운영 기준

```text
master: 10.10.10.10
worker1: 10.10.10.11
worker2: 10.10.10.12
ArgoCD UI: 10.10.10.200
Longhorn UI: 10.10.10.201
Grafana UI: 10.10.10.202
GitOps repo: https://github.com/aegis-pi/safe-edge-config-main.git
safe-edge-ai-apps revision: 8e9ae861d9e374e24edaba5efbe63c785292878a
```

## 문서 상태 규칙

- `source of truth`: 현재 구현/운영 기준 문서
- `draft`: 방향은 있으나 세부값이 미정인 문서
- `candidate`: 후속 확장 또는 검토용 문서

## 작성 원칙

- 완료된 `factory-a` 내용과 후속 Hub 확장 내용을 섞지 않는다.
- SSH 비밀번호, 토큰, 인증 정보는 문서에 기록하지 않는다.
- ArgoCD repo 등록과 dashboard 등록처럼 UI에서 수행하는 작업은 UI 절차로 명시한다.
- 테스트 결과는 시간, 측정 기준, 해석을 함께 남긴다.

## 다음 문서 업데이트 우선순위

1. `architecture/00_current_architecture.md`
2. `architecture/01_target_architecture.md`
3. `specs/monitoring_dashboard/00_requirements.md`
4. `demo/01_demo_scenario.md`
5. `report/00_executive_summary.md`
