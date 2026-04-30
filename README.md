# Aegis-Pi Risk Twin

> Safe-Edge 기반 단일 공장 엣지를 멀티 공장 중앙 관제 구조로 확장하는 Risk Twin 플랫폼

## 프로젝트 개요

기존 Safe-Edge는 Raspberry Pi 3-node K3s 클러스터 기반의 단일 공장 엣지 모니터링 시스템이다.
Aegis-Pi는 이 기준선을 먼저 `factory-a`로 복구하고, 이후 AWS Hub와 테스트베드 Spoke로 확장한다.

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | Aegis-Pi Risk Twin |
| 현재 단계 | `factory-a` Safe-Edge 기준선 구축 및 검증 완료 |
| 현재 완료 범위 | M0 `factory-a` |
| 후속 범위 | Edge Agent, AWS Hub, Dashboard VPC, `factory-b`, `factory-c`, IoT Core, S3, Risk Twin |

## 현재 완료된 Factory-A 기준선

```text
Cluster: Raspberry Pi 3-node K3s
K3s: v1.34.6+k3s1
master: 10.10.10.10
worker1: 10.10.10.11
worker2: 10.10.10.12

ArgoCD UI: 10.10.10.200
Longhorn UI: 10.10.10.201
Grafana UI: 10.10.10.202

GitOps repo: https://github.com/aegis-pi/safe-edge-config-main.git
```

현재 `factory-a`에서 완료된 항목:

- K3s 3-node cluster
- Longhorn PVC storage
- MetalLB 내부 IP 노출
- ArgoCD Helm 설치
- GitHub GitOps repo 기반 배포
- `monitoring`, `ai-apps` ArgoCD Application 분리
- InfluxDB `safe_edge_db` 1일 retention
- Grafana InfluxDB dashboard
- Prometheus Node Exporter Full `1860` dashboard
- worker2 preferred affinity + 30초 `tolerationSeconds`
- master OS cron 기반 Kubernetes-only failback
- `safe-edge-image-prepull` DaemonSet
- AI event snapshot node-local hostPath + 24시간 cleanup + 매일 03:00 KST purge
- AI inference result는 InfluxDB PVC를 통해 Longhorn 저장
- worker2 LAN 제거 장애 테스트
- worker2 `k3s-agent` 중지 장애 테스트
- 과거 worker2 전원 제거 장애 테스트

## 현재 로컬 구조

```text
factory-a
├── master  (10.10.10.10)
├── worker1 (10.10.10.11, failover standby)
└── worker2 (10.10.10.12, sensor / AI / audio preferred)
```

Namespace:

```text
argocd
longhorn-system
monitoring
ai-apps
```

## 현재 배포 흐름

```text
safe-edge-config-main GitHub repo
    -> ArgoCD UI refresh / sync
    -> safe-edge-monitoring
    -> safe-edge-ai-apps
    -> factory-a K3s
```

현재는 로컬 `factory-a` GitOps 기준선이 완료된 상태다. GitHub Actions, ECR, AWS Hub ApplicationSet은 후속 단계에서 진행한다.

## 현재 데이터 흐름

```text
BME280 / camera / mic / AI
    -> ai-apps workloads
    -> InfluxDB safe_edge_db
    -> Grafana dashboard
```

저장 정책:

- InfluxDB retention: 1일
- AI event snapshot: `/app/snapshots`
- AI event snapshot backing: node-local `/var/lib/safe-edge/snapshots`
- AI snapshot cleanup: 24시간 초과 이미지 삭제
- AI snapshot daily purge: 매일 03:00 KST 전체 비우기
- AI inference result: InfluxDB PVC를 통해 Longhorn에 저장

## 장애 검증 결과

LAN 제거 테스트:

```text
Failover: 성공
Failback: 성공
AI/audio/BME worker1 Running 성공
worker2 복구 후 worker2 failback 성공
Longhorn Multi-Attach 재발 없음
10초 bucket 기준 데이터 공백: AI/audio 약 80초, BME 약 70초
```

`k3s-agent` 중지 테스트:

```text
Failover: 성공
Failback: 성공
AI/audio/BME worker1 Running 성공
worker2 복구 후 worker2 failback 성공
Longhorn Multi-Attach 재발 없음
```

LAN 제거 InfluxDB 공백:

```text
1초 bucket:
  ai_detection:        87초
  acoustic_detection:  90초
  environment_data:    83초

10초 bucket 운영 기준:
  ai_detection:        80초
  acoustic_detection:  80초
  environment_data:    70초
```

## 목표 확장 구조

```text
AWS EKS Hub
    ├── factory-a  (현재 완료된 운영형 Raspberry Pi Safe-Edge)
    ├── factory-b  (후속 Mac mini VM 테스트베드)
    └── factory-c  (후속 Windows VM 테스트베드)

Dashboard VPC
    └── Route53 / ALB / WAF / Auth / Dashboard Web API
```

후속 확장에서는 `edge-agent`를 추가해 `factory-a` 로컬 데이터와 노드/장치/워크로드 상태를 AWS IoT Core로 송신하고, IoT Core, S3, latest status store, Risk Score Engine, ApplicationSet 기반 배포를 추가한다.

관리자 대시보드는 Tailscale에 의존하지 않는 Dashboard VPC에서 제공한다. Dashboard VPC는 Processing VPC와 VPC Peering 없이 processed S3와 latest status store를 read-only IAM으로 조회한다.

## 구현 단계

| 단계 | 내용 | 상태 |
| --- | --- | --- |
| Phase 0 | 문서 기준선 고정 | 완료 |
| Phase 1 (M0) | `factory-a` Safe-Edge 기준선 구축 | 완료 |
| Phase 2 (M1) | AWS EKS Hub 기준선 구성 | 대기 |
| Phase 3 (M2) | Hub-Spoke 연결 | 대기 |
| Phase 4 (M3~M4) | Edge Agent, 배포/데이터 파이프라인 확장 | 대기 |
| Phase 5 (M5) | `factory-b`, `factory-c` 테스트베드 확장 | 대기 |
| Phase 6 (M6) | Risk Twin + Dashboard VPC 관제 화면 | 대기 |
| Phase 7 (M7) | 통합 검증 | 대기 |

## 문서 구조

```text
docs/
├── README.md
├── issues/
├── changes/
├── ops/
│   ├── 00_quick_start.md
│   ├── 01_safe_edge_bootstrap.md
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

## 추천 읽기 순서

1. `docs/ops/05_factory_a_status.md`
2. `docs/ops/00_quick_start.md`
3. `docs/ops/06_argocd_gitops.md`
4. `docs/ops/07_grafana_dashboard.md`
5. `docs/ops/08_data_retention.md`
6. `docs/ops/09_failover_failback_test_results.md`
7. `docs/ops/10_edge_workload_placement.md`
8. `docs/ops/11_ansible_test_automation.md`
9. `docs/planning/06_edge_agent_deployment_plan.md`
10. `docs/planning/07_dashboard_vpc_extension_plan.md`
11. `docs/planning/08_aws_cli_mfa_terraform_access.md`
12. `docs/issues/M0_factory-a_safe-edge-baseline.md`

## 문서 상태 기준

| 상태 | 의미 |
| --- | --- |
| `source of truth` | 현재 구현/운영 기준 문서 |
| `draft` | 방향은 있으나 세부값 미정 |
| `candidate` | 후속 확장 또는 검토용 |

기준일: 2026-04-29
