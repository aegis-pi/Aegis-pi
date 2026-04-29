# Factory-A 현재 상태

상태: source of truth
기준일: 2026-04-29

## 목적

현재 `factory-a` Safe-Edge 기준선의 실제 운영 상태를 한 장으로 정리한다.

## 클러스터

| 항목 | 값 |
| --- | --- |
| cluster | Raspberry Pi 3-node K3s |
| K3s | `v1.34.6+k3s1` |
| master | `10.10.10.10` |
| worker1 | `10.10.10.11` |
| worker2 | `10.10.10.12` |

## 서비스 주소

| 서비스 | 주소 |
| --- | --- |
| ArgoCD | `http://10.10.10.200` |
| Longhorn | `http://10.10.10.201` |
| Grafana | `http://10.10.10.202` |

## GitOps

| 항목 | 값 |
| --- | --- |
| repo | `https://github.com/aegis-pi/safe-edge-config-main.git` |
| repo path | `monitoring/`, `ai-apps/` |
| Aegis-pi reference | `docs/ops/06_argocd_gitops.md` |
| monitoring app | `safe-edge-monitoring` |
| ai app | `safe-edge-ai-apps` |
| latest verified ai revision | `8e9ae861d9e374e24edaba5efbe63c785292878a` |

## Namespace

```text
argocd
longhorn-system
monitoring
ai-apps
```

## 주요 Workload

```text
monitoring:
- grafana: master
- influxdb: worker1
- prometheus: worker1

ai-apps:
- bme280-sensor: worker2
- safe-edge-integrated-ai: worker2
- safe-edge-audio: worker2
- safe-edge-image-prepull

argocd:
- argocd components: worker1
```

후속 planned workload:

```text
edge-agent: not deployed
planned namespace: ai-apps
planned placement: worker2 preferred, worker1 failover, master avoid
planned role: InfluxDB/Kubernetes API 기반 상태 수집 후 AWS IoT Core 송신
```

## 저장소

```text
InfluxDB PVC: Longhorn
AI snapshot: node-local /var/lib/safe-edge/snapshots, mounted at /app/snapshots
AI inference result: InfluxDB PVC -> Longhorn
InfluxDB retention: 1d
AI snapshot retention: 24h cleanup sidecar
AI snapshot daily purge: worker1/worker2 CronJob, 03:00 KST
```

## 최신 검증 요약

```text
2026-04-29 test_08:
worker2 k3s-agent 중지 -> AI/audio/BME worker1 failover 성공
worker2 k3s-agent 복구 -> AI/audio/BME worker2 failback 성공

2026-04-29 test_09:
worker2 랜선 제거 -> AI/audio/BME worker1 failover 성공
worker2 랜선 재연결 -> AI/audio/BME worker2 failback 성공
Longhorn Multi-Attach 재발 없음
InfluxDB 데이터 공백: 10초 bucket 기준 AI/audio 80초, BME 70초
```

## 시작 시 확인 명령

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get pvc
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

정상 기준:

```text
All nodes Ready
ArgoCD apps Synced / Healthy
Grafana master Running
ArgoCD worker1 Running
Prometheus/InfluxDB worker1 Running
AI/audio/BME target Pods worker2 Running
Longhorn volumes healthy
Grafana dashboard 갱신
```
