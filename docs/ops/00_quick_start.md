# Quick Start

상태: source of truth
기준일: 2026-05-19

## 목적

현재 `factory-a` Safe-Edge 기준선의 상태를 빠르게 확인하고, 다음 운영 문서로 이동할 수 있게 안내한다.

## 현재 상태

- `factory-a` 로컬 Raspberry Pi 3-node K3s 기준선 구축이 완료됐다.
- ArgoCD, Longhorn, Grafana, InfluxDB, AI/Audio/BME280 워크로드가 동작한다.
- AWS Hub EKS/VPC/namespace/ArgoCD bootstrap 기준선은 `scripts/build/build-hub.sh`로 재생성 가능하다. 현재 build 흐름은 Hub와 factory cluster 등록을 먼저 끝내고, IoT Secret 준비 후 Spoke ApplicationSet을 배포하도록 분리되어 있다.
- Foundation S3 bucket `aegis-bucket-data`, AMP Workspace `AEGIS-AMP-hub`, ECR, IoT Rule은 Hub destroy와 분리되는 foundation 리소스다.
- IoT Core `factory-a` Thing/certificate/policy와 K3s Secret은 `scripts/build/build-iot-factory-a.sh`에서 생성/갱신한다. 같은 단계에서 ArgoCD ApplicationSet을 적용해 `factory-a` data-plane workload 배포를 시작한다.
- `risk/risk-normalizer` IRSA S3 권한과 `observability/prometheus-agent` AMP remote_write 수신은 검증 완료 상태다. 단, `risk/risk-normalizer`는 M1 권한 검증 이력이며 최신 데이터 처리 구현 대상은 Lambda data processor와 DynamoDB/S3 processed다.
- Hub Prometheus Agent는 rebuild 시 `observability` 네임스페이스에서 재설치되며, 이전 검증에서는 AMP Query API로 `up{cluster="AEGIS-EKS"}` 수신을 확인했다.
- 내부 Grafana는 rebuild 시 `observability` 네임스페이스에서 재설치되며, 이전 검증에서는 AMP datasource `AEGIS-AMP`가 SigV4 + IRSA로 query 가능했다.
- AWS Load Balancer Controller와 Admin UI HTTPS Ingress는 `scripts/build/build-admin-ui-after-ns.sh`로 ACM 발급 확인 후 활성화한다.
- `factory-b`, `factory-c`, Dashboard VPC는 후속 단계다. ECR/GitHub Actions CI, Tailscale Hub-Spoke, `factory-a` ApplicationSet data-plane 배포 기준선은 준비됐다.
- 후속 구현은 Terraform = 인프라, Ansible = bootstrap/설정/소프트웨어, GitHub Actions = CI, GitHub+ArgoCD = CD 기준을 따른다.

## 현재 운영 주소

| 항목 | 값 |
| --- | --- |
| master | `10.10.10.10` |
| worker1 | `10.10.10.11` |
| worker2 | `10.10.10.12` |
| ArgoCD UI | `http://10.10.10.200` |
| Longhorn UI | `http://10.10.10.201` |
| Grafana UI | `http://10.10.10.202` |
| GitOps repo | `https://github.com/aegis-pi/safe-edge-config-main.git` |

## 우선 읽을 문서

1. `docs/ops/05_factory_a_status.md`
2. `docs/ops/06_argocd_gitops.md`
3. `docs/ops/07_grafana_dashboard.md`
4. `docs/ops/08_data_retention.md`
5. `docs/ops/09_failover_failback_test_results.md`
6. `docs/ops/04_troubleshooting.md`
7. `docs/changes/README.md`
8. `docs/ops/14_hub_run_commands.md`

## 빠른 상태 확인

master에서 확인한다.

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n monitoring get pvc
kubectl -n ai-apps get pvc
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

정상 기준:

```text
master, worker1, worker2: Ready
safe-edge-monitoring: Synced / Healthy
safe-edge-ai-apps: Synced / Healthy
monitoring/influxdb, prometheus, grafana: Running
ai-apps/bme280-sensor, safe-edge-integrated-ai, safe-edge-audio: worker2 Running
safe-edge-image-prepull: worker1, worker2 Running
Longhorn volumes: attached / healthy
```

## 현재 완료된 범위

```text
K3s 3-node 구성
Longhorn PVC 저장소
MetalLB 내부 IP 노출
ArgoCD Helm 설치
GitHub GitOps repo 기반 배포
monitoring / ai-apps Application 분리
InfluxDB safe_edge_db 1일 retention
Grafana InfluxDB dashboard 구성
Prometheus Node Exporter Full 1860 dashboard 사용
worker2 preferred affinity + 30초 tolerationSeconds
master OS cron 기반 Kubernetes-only failback
safe-edge-image-prepull DaemonSet
AI snapshot node-local hostPath + 24시간 cleanup + 매일 03:00 KST purge
AI inference result InfluxDB PVC 기반 Longhorn 저장
LAN 제거 장애 테스트
k3s-agent 중지 장애 테스트
Hub EKS ArgoCD + Tailscale factory-a cluster 등록 자동화
aegis-pi-gitops ApplicationSet 기반 factory-a data-plane 배포
IoT Core -> S3 raw 적재 검증
```

## 다음 단계

1. 계획과 실제 구현이 달라진 항목은 `docs/changes/`에 Change Record로 남긴다.
2. `README.md`, `docs/README.md`, architecture 문서를 현재 `factory-a` 기준으로 유지한다.
3. Grafana/dashboard 스펙을 실제 InfluxDB + Prometheus 기준으로 유지한다.
4. M1 Issue 9 AWS Load Balancer Controller, M1 Issue 10 ArgoCD/Grafana HTTPS Admin Ingress, M1 Issue 12 `runtime-config.yaml` 구조 초안, M3 Issue 1~5 배포 기준선, M4 Issue 1~5 data-plane 구현/적재 검증은 완료됐다. 다음 작업은 M4 Issue 6 Lambda data processor와 M5 factory 확장이다.
