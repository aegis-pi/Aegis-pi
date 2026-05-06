# Quick Start

상태: source of truth
기준일: 2026-05-06

## 목적

현재 `factory-a` Safe-Edge 기준선의 상태를 빠르게 확인하고, 다음 운영 문서로 이동할 수 있게 안내한다.

## 현재 상태

- `factory-a` 로컬 Raspberry Pi 3-node K3s 기준선 구축이 완료됐다.
- ArgoCD, Longhorn, Grafana, InfluxDB, AI/Audio/BME280 워크로드가 동작한다.
- AWS Hub EKS/VPC/namespace/ArgoCD bootstrap 기준선은 2026-05-06 `build-all --admin-ui`와 `build-hub`로 재생성/검증되어 active 상태다.
- Foundation S3 bucket `aegis-bucket-data`, AMP Workspace `AEGIS-AMP-hub`, IoT Rule -> S3 raw 적재는 active 상태다.
- IoT Core `factory-a` Thing/certificate/policy와 K3s Secret은 active 상태다.
- `risk/risk-normalizer` IRSA S3 권한과 `observability/prometheus-agent` AMP remote_write 수신은 검증 완료 상태다.
- Hub Prometheus Agent는 `observability` 네임스페이스에서 Running이며 AMP Query API로 `up{cluster="AEGIS-EKS"}` 수신을 확인했다.
- 내부 Grafana는 `observability` 네임스페이스에서 Running이며 AMP datasource `AEGIS-AMP`가 SigV4 + IRSA로 query 가능한 상태다.
- AWS Load Balancer Controller와 Admin UI HTTPS Ingress가 활성화되어 `https://argocd.minsoo-tech.cloud`, `https://grafana.minsoo-tech.cloud` 접근을 검증했다.
- `factory-b`, `factory-c`, ECR, GitHub Actions CI, Dashboard VPC, Tailscale/Hub-Spoke 연결은 후속 단계다.
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
```

## 다음 단계

1. 계획과 실제 구현이 달라진 항목은 `docs/changes/`에 Change Record로 남긴다.
2. `README.md`, `docs/README.md`, architecture 문서를 현재 `factory-a` 기준으로 유지한다.
3. Grafana/dashboard 스펙을 실제 InfluxDB + Prometheus 기준으로 유지한다.
4. M1 Issue 9 AWS Load Balancer Controller와 M1 Issue 10 ArgoCD/Grafana HTTPS Admin Ingress는 완료됐다. 다음 Hub 작업은 M1 Issue 12의 `runtime-config.yaml` 구조 초안 작성이다.
