# Ops Docs

이 디렉터리는 실제 운영, 점검, 장애 대응, 인증서 주입 같은 실행 절차 문서를 둔다.

현재 운영 기준일은 2026-06-08다. Hub-only 데이터 수집 유지 재시작은 `14_hub_run_commands.md`, data-pipeline과 Cloud collector는 `23_data_pipeline.md` 및 `29_cloud_infra_metrics_pipeline_plan.md`, Slack alert 정책은 `31_risk_alert_dispatcher.md`, factory-a image snapshot S3 upload는 `32_image_snapshot_pipeline.md`, factory-a AI latency 기준은 `33_factory_a_ai_latency_measurement.md`를 source of truth로 사용한다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `00_quick_start.md` | `factory-a` 현재 상태와 빠른 확인 명령 |
| `01_safe_edge_bootstrap.md` | Safe-Edge 기준선 구축 절차 |
| `02_self_check.md` | 운영자가 직접 상태를 점검하는 기준 |
| `03_test_checklist.md` | 장애/데이터/통합 테스트 체크리스트 |
| `04_troubleshooting.md` | 구축과 운영 중 발생한 문제와 해결 기록 |
| `05_factory_a_status.md` | `factory-a`의 최신 운영 상태 요약 |
| `06_argocd_gitops.md` | ArgoCD GitOps 운영 방식 |
| `07_grafana_dashboard.md` | Grafana dashboard 구성과 확인 기준 |
| `08_data_retention.md` | InfluxDB, snapshot, Longhorn 데이터 보존 기준 |
| `09_failover_failback_test_results.md` | failover/failback 검증 결과 |
| `10_edge_workload_placement.md` | Edge workload 배치 정책 |
| `11_ansible_test_automation.md` | Ansible 기반 반복 점검 자동화 계획 |
| `12_iot_core_thing_secret_mount.md` | IoT Core Thing 등록과 K3s Secret mount 절차 |
| `13_hub_namespace_baseline.md` | Hub EKS namespace 기준 |
| `14_hub_run_commands.md` | Hub/Admin UI/IoT/Spoke 배포와 최종 검증 실행 명령어 |
| `15_aws_cost_baseline.md` | AWS Hub 시간당 비용 기준과 갱신 규칙 |
| `16_hub_prometheus_amp.md` | retired Hub Prometheus Agent/AMP 기준과 cleanup 절차 |
| `17_hub_grafana_amp.md` | Hub 내부 Grafana 운영 기준 |
| `18_factory_b_mac_utm_k3s.md` | Mac UTM 기반 `factory-b` 테스트베드 K3s 구성 사전 |
| `19_factory_c_windows_virtualbox_k3s.md` | Windows VirtualBox 기반 `factory-c` 테스트베드 K3s 구성 사전 |
| `20_tailscale_hub_spoke_runbook.md` | Tailscale 기반 Hub-Spoke 연결 실행 절차 |
| `21_hub_admin_ui_ingress.md` | ArgoCD/Grafana 관리자 HTTPS Ingress 운영 절차 |
| `22_factory_bc_testbed_data_plane.md` | `factory-b/c` 로컬 dummy generator, hostPath outbox, 공통 publisher 기준 |
| `23_data_pipeline.md` | IoT Rule, Lambda data processor, DynamoDB/S3 processed 운영 기준 |
| `24_daily_factory_report.md` | Bedrock 기반 factory별 일일 운영 보고서 운영 기준 |
| `25_daily_factory_report_cost.md` | Daily Factory Report 1회/월간 비용 산정 기준 |
| `26_dynamodb_key_model.md` | DynamoDB `AEGIS-DynamoDB-FactoryStatus` PK/SK 구조와 현재 키 패턴 |
| `27_dummy_data_generation_and_risk_scenarios.md` | `factory-b/c` dummy data 생성, outbox cleanup, Risk Score 계산, scenario 운영 기준 |
| `28_data_pipeline_refresh_flow_explained.md` | 데이터가 끊겼을 때 refresh, LATEST/HISTORY, processed_agg가 어떻게 동작하는지 설명 |
| `29_cloud_infra_metrics_pipeline_plan.md` | Cloud infra metric을 필요한 항목만 수집해 DynamoDB/S3 read model로 저장하는 구현/운영 기준 |
| `30_factory_bc_dummy_generator_risk_coverage_backtest.md` | `factory-b/c` dummy generator risk coverage 수정, VM 배포, DynamoDB/S3 backtest 결과 |
| `31_risk_alert_dispatcher.md` | S3 processed snapshot 기반 RiskAlertDispatcher Lambda, DynamoDB dedupe, Slack webhook routing 운영 기준 |
| `32_image_snapshot_pipeline.md` | factory-a AI snapshot S3 upload, presigned URL, `image_snapshot` metadata data-pipeline 운영/검증 |
| `33_factory_a_ai_latency_measurement.md` | factory-a `safe-edge-integrated-ai` loop 주기, YOLO 추론 시간, 측정 한계와 instrumentation 기준 |

## 기준

- 현재 실제 운영 절차는 이 디렉터리의 문서를 우선한다.
- Git Wiki에 올릴 트러블슈팅 리포트 형식 변환본은 `../wiki/troubleshooting/`을 따른다.
- 비밀번호, token, private key, certificate 원문은 문서에 기록하지 않는다.
- AWS 리소스, 상시 실행 컴포넌트, 저장소, 네트워크 경로가 추가되면 `15_aws_cost_baseline.md`의 비용 기준을 함께 갱신한다.
