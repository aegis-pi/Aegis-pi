# Aegis-Pi Risk Twin

> Safe-Edge 기반 단일 공장 엣지를 멀티 공장 중앙 관제 구조로 확장하는 Risk Twin 플랫폼

## 프로젝트 개요

기존 Safe-Edge는 Raspberry Pi 3-node K3s 클러스터 기반의 단일 공장 엣지 모니터링 시스템이다.
Aegis-Pi는 이 기준선을 먼저 `factory-a`로 복구하고, 이후 AWS Hub와 테스트베드 Spoke로 확장한다.

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | Aegis-Pi Risk Twin |
| 현재 단계 | M1 Hub 클라우드 기반 구성 |
| 현재 완료 범위 | M0 `factory-a`, M1 Issue 0~10 완료. IoT Rule -> S3 raw 적재, IRSA S3/AMP 권한, Hub Prometheus Agent -> AMP remote_write, 내부 Grafana -> AMP query, AWS Load Balancer Controller, Admin UI HTTPS Ingress 검증 완료 |
| 현재 AWS 상태 | 2026-05-06 `build-hub` 및 Admin UI 활성화 완료. Hub EKS/VPC/NAT/EIP, ArgoCD, Prometheus Agent, Grafana, foundation S3/AMP/IoT Rule, Route53/ACM, Admin UI ALB, `factory-a` IoT/K3s Secret active 확인. ACM certificate는 `ISSUED`, 과거 KMS keys는 `PendingDeletion` |
| 다음 작업 | M1 Issue 12 `runtime-config.yaml` 파일 구조 초안. Issue 11 운영 보안 강화는 MVP 이후로 보류 |
| 비용 기준 | 현재 Hub active + Admin UI ALB 고정 비용 `~$0.36/hour` 기준. 상세 기준은 `docs/ops/15_aws_cost_baseline.md` |

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

## 현재 Hub bootstrap 기준

M1 Issue 0~10에서는 AWS MFA/Terraform 접근, Hub EKS/VPC 기준선, Hub namespace 기준선, Hub ArgoCD bootstrap, foundation S3 data bucket `aegis-bucket-data`, AMP Workspace `AEGIS-AMP-hub`, `factory-a` IoT Thing/certificate/policy/K3s Secret, IoT Rule -> S3 `raw/` prefix 적재, `risk/risk-normalizer` IRSA S3 권한, `observability/prometheus-agent` 설치 및 AMP remote_write 수신, Grafana AMP datasource query, AWS Load Balancer Controller, Route53/ACM, ArgoCD/Grafana HTTPS Admin Ingress를 검증했다.

2026-05-06 기준 `scripts/build/build-all.sh --admin-ui` 및 `scripts/build/build-hub.sh` 실행으로 Hub, foundation, Admin UI 리소스는 active 상태다. 기본 전체 재생성은 `scripts/build/build-all.sh`, Admin UI까지 포함한 재생성은 `scripts/build/build-all.sh --admin-ui`, 전체 삭제는 `scripts/destroy/destroy-all.sh`를 사용한다. 비용 기준은 `docs/ops/15_aws_cost_baseline.md`를 따른다.

앞으로 모든 작업은 `docs/planning/11_delivery_ownership_flow.md`의 책임 경계를 따른다.

책임 범위는 아래처럼 분리한다.

| 경로 | 역할 | 현재 상태 |
| --- | --- | --- |
| `infra/hub` | VPC, subnet, NAT Gateway, EKS cluster, node group, Route53/ACM, EKS OIDC 기반 IRSA | active, Terraform state present |
| `scripts/ansible/playbooks` | kubeconfig 갱신, namespace, LimitRange, ArgoCD Helm install, Prometheus Agent remote_write, Grafana AMP datasource, AWS Load Balancer Controller, Admin UI Ingress bootstrap/검증 | active, rebuild 시 재실행 |
| `infra/foundation` | S3, AMP Workspace, IoT Rule 같은 EKS destroy와 분리할 영속 리소스 | active, Terraform state present |

Hub 기본값:

```text
Region: ap-south-1
VPC CIDR: 10.0.0.0/16
AZ: ap-south-1a, ap-south-1c
EKS: AEGIS-EKS
Kubernetes: 1.34
Node group: AEGIS-EKS-node, t3.medium x 2
Naming: AEGIS-[resource]-[feature]-[zone]
```

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

후속 확장에서는 `edge-agent`를 추가해 `factory-a` 로컬 데이터와 노드/장치/워크로드 상태를 AWS IoT Core로 송신하고, IoT Core -> S3 데이터 플레인, latest status store, Risk Score Engine, ApplicationSet 기반 배포를 추가한다.

관리자 대시보드는 Tailscale에 의존하지 않는 Dashboard VPC에서 제공한다. Dashboard VPC는 Processing VPC와 VPC Peering 없이 processed S3와 latest status store를 read-only IAM으로 조회한다.

## 구현 단계

| 단계 | 내용 | 상태 |
| --- | --- | --- |
| Phase 0 | 문서 기준선 고정 | 완료 |
| Phase 1 (M0) | `factory-a` Safe-Edge 기준선 구축 | 완료 |
| Phase 2 (M1) | AWS EKS Hub 기준선 구성 | 진행 중, Issue 0~10 완료, Issue 11 보류, Issue 12 대기 |
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
│   ├── 11_ansible_test_automation.md
│   ├── 12_iot_core_thing_secret_mount.md
│   ├── 13_hub_namespace_baseline.md
│   ├── 14_hub_run_commands.md
│   └── 15_aws_cost_baseline.md
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

```text
infra/
├── hub/
├── foundation/
├── safe-edge/
├── mesh-vpn/
└── deploy/
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
12. `docs/planning/09_m1_eks_vpc_decision_record.md`
13. `docs/planning/11_delivery_ownership_flow.md`
14. `docs/issues/M0_factory-a_safe-edge-baseline.md`
15. `docs/issues/M1_hub-cloud.md`
16. `docs/ops/13_hub_namespace_baseline.md`
17. `docs/ops/14_hub_run_commands.md`

## 문서 상태 기준

| 상태 | 의미 |
| --- | --- |
| `source of truth` | 현재 구현/운영 기준 문서 |
| `draft` | 방향은 있으나 세부값 미정 |
| `candidate` | 후속 확장 또는 검토용 |

기준일: 2026-05-04
