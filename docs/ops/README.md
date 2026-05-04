# Ops Docs

이 디렉터리는 실제 운영, 점검, 장애 대응, 인증서 주입 같은 실행 절차 문서를 둔다.

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
| `14_hub_run_commands.md` | Hub 실행 및 ArgoCD 초기 비밀번호 확인 명령어 |

## 기준

- 현재 실제 운영 절차는 이 디렉터리의 문서를 우선한다.
- 비밀번호, token, private key, certificate 원문은 문서에 기록하지 않는다.
