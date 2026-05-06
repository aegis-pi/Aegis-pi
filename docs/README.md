# Aegis-Pi Docs

상태: source of truth
기준일: 2026-05-06

## 목적

이 디렉터리는 Aegis-Pi 프로젝트의 설계, 운영, 검증, 시연, 보고 문서를 관리한다.

## 현재 상태

- 현재 완료된 구현 범위는 `factory-a` Safe-Edge 기준선과 M1 Hub Issue 0~10이다.
- `factory-a`는 Raspberry Pi 3-node K3s 기반 운영형 Spoke다.
- 2026-04-30 기준 AI snapshot은 node-local hostPath를 사용하며, AI 추론 결과는 InfluxDB PVC를 통해 Longhorn에 저장한다.
- 2026-04-30 기준 LAN 제거 및 `k3s-agent` 중지 failover/failback 재검증을 완료했다.
- 2026-05-06 `build-all --admin-ui` 및 `build-hub` 실행 후 AWS Hub EKS/VPC/NAT/EIP, foundation S3 bucket, AMP Workspace, IoT Rule, Route53/ACM, AWS Load Balancer Controller, Admin UI ALB, `factory-a` IoT/K3s Secret은 active 확인 상태다.
- M1 Issue 5에서 IoT Rule -> S3 raw 적재와 `risk/risk-normalizer` IRSA S3 권한 검증을 완료했다.
- M1 Issue 6에서 AMP Workspace와 `observability/prometheus-agent` IRSA remote_write 권한 검증을 완료했다.
- M1 Issue 7에서 Hub Prometheus Agent를 설치하고 AMP Query API로 `up{cluster="AEGIS-EKS"}` 수신을 검증했다.
- M1 Issue 8에서 내부 Grafana를 설치하고 AMP datasource를 SigV4 + IRSA로 검증했다.
- M1 Issue 9에서 AWS Load Balancer Controller를 설치하고 IRSA/subnet discovery 기준을 검증했다.
- M1 Issue 10에서 `argocd.minsoo-tech.cloud`, `grafana.minsoo-tech.cloud` HTTPS Admin Ingress를 공유 Public ALB로 검증했다.
- 다음 작업은 M1 Issue 12 `runtime-config.yaml` 구조 초안이다. M1 Issue 11 운영 보안 강화는 MVP 이후로 보류했다.
- `factory-b`, `factory-c`, ECR, GitHub Actions CI, Tailscale은 후속 단계다.
- 현재 운영 source of truth는 `docs/ops/` 문서다.
- 마일스톤 추적은 `docs/issues/` 문서를 따른다.
- 계획과 실제 구현이 달라진 결정은 `docs/changes/`에서 추적한다.
- 후속 관리자 대시보드는 `planning/07_dashboard_vpc_extension_plan.md`의 Dashboard VPC 방향을 따른다.
- AWS CLI MFA 및 Terraform 접근 준비는 `planning/08_aws_cli_mfa_terraform_access.md`를 따른다.
- 인프라/설정/CI/CD 책임 경계는 `planning/11_delivery_ownership_flow.md`를 따른다.
- M1 EKS/VPC 설계 결정은 `planning/09_m1_eks_vpc_decision_record.md`를 따른다.
- AWS 리소스 비용 기준과 갱신 규칙은 `ops/15_aws_cost_baseline.md`를 따른다.

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
10. `ops/12_iot_core_thing_secret_mount.md`
11. `changes/README.md`
12. `planning/06_edge_agent_deployment_plan.md`
13. `planning/07_dashboard_vpc_extension_plan.md`
14. `planning/08_aws_cli_mfa_terraform_access.md`
15. `planning/09_m1_eks_vpc_decision_record.md`
16. `planning/11_delivery_ownership_flow.md`
17. `ops/13_hub_namespace_baseline.md`
18. `ops/14_hub_run_commands.md`
19. `ops/15_aws_cost_baseline.md`
20. `ops/16_hub_prometheus_amp.md`
21. `ops/17_hub_grafana_amp.md`
22. `ops/20_tailscale_hub_spoke_runbook.md`
23. `ops/21_hub_admin_ui_ingress.md`
24. `issues/M0_factory-a_safe-edge-baseline.md`
25. `issues/M1_hub-cloud.md`

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
│   ├── 11_ansible_test_automation.md
│   ├── 12_iot_core_thing_secret_mount.md
│   ├── 13_hub_namespace_baseline.md
│   ├── 14_hub_run_commands.md
│   ├── 15_aws_cost_baseline.md
│   ├── 16_hub_prometheus_amp.md
│   ├── 17_hub_grafana_amp.md
│   ├── 18_factory_b_mac_utm_k3s.md
│   ├── 19_factory_c_windows_virtualbox_k3s.md
│   ├── 20_tailscale_hub_spoke_runbook.md
│   └── 21_hub_admin_ui_ingress.md
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
│   ├── 08_aws_cli_mfa_terraform_access.md
│   ├── 09_m1_eks_vpc_decision_record.md
│   ├── 10_portfolio_idea_assessment.md
│   └── 11_delivery_ownership_flow.md
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

## 현재 Hub 기준

```text
AWS actual state: Hub/Foundation/IoT/Admin UI active after `scripts/build/build-all.sh --admin-ui`; historical KMS keys are `PendingDeletion`
Hub bootstrap roots:
- infra/hub: VPC/EKS/node group, Route53/ACM, IRSA
- scripts/ansible: namespace/LimitRange/ArgoCD/Prometheus Agent/Grafana/AWS Load Balancer Controller/Admin UI Ingress bootstrap
- infra/foundation: S3 data bucket, AMP Workspace, IoT Rule, and future durable resources
Build entrypoint: scripts/build/build-all.sh
Admin UI build entrypoint: scripts/build/build-all.sh --admin-ui
Hub UI entrypoint: https://argocd.minsoo-tech.cloud and https://grafana.minsoo-tech.cloud
Local fallback UI entrypoint: scripts/ops/argocd-port-forward.sh, scripts/ops/grafana-port-forward.sh
Hub destroy entrypoint: scripts/destroy/destroy-hub.sh
Cost baseline: docs/ops/15_aws_cost_baseline.md
Delivery flow: Terraform -> Ansible -> GitHub Actions CI -> GitHub/ArgoCD CD
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
- AWS 리소스나 상시 운영 경로를 추가하면 비용 영향을 분석하고 `ops/15_aws_cost_baseline.md`를 갱신한다.

## 다음 문서 업데이트 우선순위

1. `architecture/00_current_architecture.md`
2. `architecture/01_target_architecture.md`
3. `specs/monitoring_dashboard/00_requirements.md`
4. `demo/01_demo_scenario.md`
5. `report/00_executive_summary.md`
