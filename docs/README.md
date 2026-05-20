# Aegis-Pi Docs

상태: source of truth
기준일: 2026-05-20

## 목적

이 디렉터리는 Aegis-Pi 프로젝트의 설계, 운영, 검증, 시연, 보고 문서를 관리한다.

## 현재 상태

- 현재 완료된 구현 범위는 `factory-a` Safe-Edge 기준선, M1 Hub Issue 0~10/12, M2 Issue 1~6, M3 Issue 1~5/7/8, M4 Issue 1~5/8, M5 Issue 1~7이다.
- `factory-a`는 Raspberry Pi 3-node K3s 기반 운영형 Spoke다.
- 2026-04-30 기준 AI snapshot은 node-local hostPath를 사용하며, AI 추론 결과는 InfluxDB PVC를 통해 Longhorn에 저장한다.
- 2026-04-30 기준 LAN 제거 및 `k3s-agent` 중지 failover/failback 재검증을 완료했다.
- 2026-05-20 기준 `build-hub.sh`는 AWS Hub EKS/VPC/NAT/EIP, ArgoCD, Prometheus Agent, Grafana, AWS Load Balancer Controller까지만 자동화한다. Admin UI HTTPS Ingress는 Route53 NS 위임 이후 `build-admin-ui-after-ns.sh`에서 실행하고, Tailnet UI 연결은 `connect-hub-tailscale-ui.sh`, Spoke ArgoCD cluster 등록은 `register-spoke-factory-a.sh`, `register-spoke-factory-b.sh`, `register-spoke-factory-c.sh`로 factory별 실행한다.
- 2026-05-20 기준 Hub-only 재시작 순서는 `build-hub.sh` -> 필요 시 `build-admin-ui-after-ns.sh` -> 필요 시 `connect-hub-tailscale-ui.sh` -> `register-spoke-factory-a/b/c.sh`다. Hub 삭제 전에는 `destroy/stop-dummy-generators.sh`로 factory-b/c VM 데이터 생성을 먼저 멈춘다.
- M1 Issue 5에서 IoT Rule -> S3 raw 적재와 M1 검증용 `risk/risk-normalizer` IRSA S3 권한 검증을 완료했다. 최신 데이터 처리 방향은 Lambda data processor와 DynamoDB/S3 processed다.
- M1 Issue 6에서 AMP Workspace와 `observability/prometheus-agent` IRSA remote_write 권한 검증을 완료했다.
- M1 Issue 7에서 Hub Prometheus Agent를 설치하고 AMP Query API로 `up{cluster="AEGIS-EKS"}` 수신을 검증했다.
- M1 Issue 8에서 내부 Grafana를 설치하고 AMP datasource를 SigV4 + IRSA로 검증했다.
- M1 Issue 9에서 AWS Load Balancer Controller를 설치하고 IRSA/subnet discovery 기준을 검증했다.
- M1 Issue 10에서 `argocd.minsoo-tech.cloud`, `grafana.minsoo-tech.cloud` HTTPS Admin Ingress를 공유 Public ALB로 검증했다.
- M1 Issue 12에서 `configs/runtime/runtime-config.yaml`과 VM dummy data 추천값을 작성했다.
- M2 Issue 1에서 Tailnet/tag/Auth Key 정책을 수립하고 Tailnet을 확인했다.
- M2 Issue 2에서 `factory-a-master` Tailscale 참여, tag 적용, Windows 운영자 PC의 ping/SSH 접근을 검증했다.
- M2 Issue 3에서 EKS Hub Tailscale Operator 설치, egress Service 생성, EKS 내부 `factory-a-master` K3s API TCP `6443` reachability, ArgoCD/Grafana Tailscale IP UI 접근 검증까지 완료했다.
- M2 Issue 4/5에서 `tls-server-name: 10.10.10.10` 기반 `factory-a` kubeconfig와 ArgoCD cluster 등록을 완료했고, cluster status `Successful`을 확인했다.
- M2 Issue 6에서 `factory-a-podinfo-smoke` Application을 `factory-a`에 Sync해 `Synced` + `Healthy`, Pod 2개 `Running`을 확인했고, Tailscale egress Service 삭제 시 sync failure 및 재생성 후 복구를 검증했다.
- M3 Issue 1에서 `aegis-pi-gitops` GitOps 저장소 구조, `aegis-spoke` Helm chart, 공장별 values, ApplicationSet skeleton, manifest validation workflow를 완료했다.
- M4 Issue 1~5/8에서 Raw 데이터 계약, `factory-a-log-adapter`, `edge-iot-publisher`, ECR 이미지, GitOps chart, IoT Core -> S3 raw 적재와 `factory-a` raw data-plane 검증을 완료했다. 다음 데이터 처리 작업은 M4 Issue 6 Lambda data processor와 M4 Issue 7 `pipeline_status` 처리 검증이다.
- 2026-05-20 기준 `factory-b`, `factory-c`는 2-node VM K3s, Tailnet 참여, Hub ArgoCD cluster Secret, ApplicationSet 기반 `aegis-spoke-factory-b/c` Application 생성 및 동기화를 완료하고, 로컬 dummy generator 및 publisher를 통한 S3 raw 적재와 시각 동기화(Chrony) 검증까지 최종 완료했다.
- `factory-b/c` 데이터 플레인은 로컬 dummy generator가 worker node hostPath `/var/lib/aegis/outbox`에 canonical JSON을 쓰고, Hub ArgoCD가 배포한 공통 `edge-iot-publisher`가 같은 hostPath를 읽어 IoT Core로 전송하도록 구축했다. GitOps chart/values는 이 hostPath 기준으로 전환했다.
- Risk Twin Dashboard는 후속 단계이며, 선행 작업은 IoT Core Lambda data processor, DynamoDB LATEST/HISTORY, S3 processed 저장 경로 구현이다.
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
24. `ops/22_factory_bc_testbed_data_plane.md`
25. `planning/16_m4_edge_data_plane_implementation.md`
26. `issues/M0_factory-a_safe-edge-baseline.md`
27. `issues/M1_hub-cloud.md`

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
│   ├── 21_hub_admin_ui_ingress.md
│   └── 22_factory_bc_testbed_data_plane.md
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
factory-a-master Tailscale IPv4: 100.117.40.125
Windows operator PC Tailscale IPv4: 100.67.181.8
```

## 현재 Hub 기준

```text
AWS actual state: Hub/Foundation/IoT/Admin UI are rebuildable through scripts/build; Hub destroy removes EKS-scoped resources, foundation/IoT/ECR are separate
Hub bootstrap roots:
- infra/hub: VPC/EKS/node group, Route53/ACM, IRSA
- scripts/ansible: namespace/LimitRange/ArgoCD/Prometheus Agent/Grafana/AWS Load Balancer Controller/Admin UI Ingress/Tailscale/Spoke ApplicationSet bootstrap
- infra/foundation: S3 data bucket, AMP Workspace, IoT Rule, and future durable resources
Build entrypoint: scripts/build/build-hub.sh
Admin UI post-NS entrypoint: scripts/build/build-admin-ui-after-ns.sh
Tailnet UI entrypoint: scripts/build/connect-hub-tailscale-ui.sh
Spoke registration entrypoints: scripts/build/register-spoke-factory-a.sh, scripts/build/register-spoke-factory-b.sh, scripts/build/register-spoke-factory-c.sh
Factory-a IoT Secret refresh entrypoint: scripts/build/build-iot-factory-a.sh
Complete verification entrypoint: scripts/build/verify-complete.sh
Hub UI entrypoint after rebuild: https://argocd.minsoo-tech.cloud and https://grafana.minsoo-tech.cloud
Local fallback UI entrypoint: scripts/ops/argocd-port-forward.sh, scripts/ops/grafana-port-forward.sh
VM dummy stop entrypoint: scripts/destroy/stop-dummy-generators.sh
Hub destroy entrypoint: scripts/destroy/destroy-hub.sh
Full destroy entrypoint: scripts/destroy/destroy-all.sh
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
