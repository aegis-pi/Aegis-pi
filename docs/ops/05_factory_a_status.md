# Factory-A 현재 상태

상태: source of truth
기준일: 2026-06-02

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

Hub 배포 data-plane workload:

```text
edge data-plane: aegis-pi-gitops ApplicationSet 기준 배포
namespace: ai-apps
placement: worker2 preferred, worker1 failover, master avoid
role: factory-a-log-adapter가 InfluxDB/Kubernetes API 기반 상태를 canonical JSON으로 변환하고 edge-iot-publisher가 AWS IoT Core로 송신
deployments:
- aegis-spoke-factory-a-log-adapter
- aegis-spoke-edge-iot-publisher
shared outbox: /var/lib/aegis/outbox (Longhorn PVC aegis-spoke-outbox)
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

2026-05-19:
Hub ArgoCD ApplicationSet -> factory-a data-plane 배포 기준 정리
IoT Secret 준비 후 ApplicationSet 배포 순서로 build 흐름 변경
verify-complete.sh로 Hub/IoT/factory-a workload 통합 검증 가능

2026-05-29:
factory-a IoT data-plane 입력은 2026-05-28T07:54Z 이후 중단된 상태로 확인됐다.
DataProcessor 1분 freshness refresh 배포 후 DynamoDB LATEST는 pipeline_status critical, risk.score 0, risk.level danger로 갱신된다.
마지막 raw infra_state는 node_summary.ready=3/3이었으나, 과거 processed/LATEST에는 구형 normalizer 결과로 nodes_ready=0/3이 남아 있다.
factory-a가 다시 infra_state를 보내면 현재 normalizer 기준으로 LATEST.infra_state가 덮어써진다.

2026-06-02:
DataProcessorRefresh1m, CloudInfra collectors, RiskAlertDispatcher는 data-pipeline 생명주기에 포함되어 동작한다.
factory-a 입력 중단 여부는 다음 운영 시작 시 DynamoDB LATEST와 S3 raw/processed 최신 timestamp를 먼저 재확인한다.
warning/danger state_snapshot이 생성되면 RiskAlertDispatcher가 factory-a Slack webhook으로 알림을 보낼 수 있다.
```

## 시작 시 확인 명령

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get pvc
kubectl -n ai-apps rollout status deployment/aegis-spoke-edge-iot-publisher
kubectl -n ai-apps rollout status deployment/aegis-spoke-factory-a-log-adapter
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
