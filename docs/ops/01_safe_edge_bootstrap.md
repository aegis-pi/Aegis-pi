# Safe-Edge 기준선 부트스트랩 가이드

상태: source of truth
기준일: 2026-04-29

## 목적

`factory-a` Safe-Edge 기준선을 현재 실제 구축 상태 기준으로 정리한다.

## 현재 상태

`factory-a` 기준선은 구축 및 장애 검증까지 완료됐다. 이 문서는 신규 구축 또는 재구축 시 따라야 할 기준 순서와 완료 상태를 함께 기록한다.

## 목표 상태

```text
Raspberry Pi 3-node K3s cluster
master: control plane
worker1: failover standby
worker2: sensor / AI / audio preferred node
Longhorn: local replicated storage
ArgoCD: Helm 기반 GitOps 배포
Grafana: InfluxDB + Prometheus dashboard
InfluxDB: safe_edge_db, 1일 retention
AI snapshots: node-local hostPath, 24시간 초과 자동 삭제, 매일 03:00 KST purge
AI inference result: InfluxDB PVC를 통해 Longhorn 저장
Failback: master OS cron 기반 Kubernetes-only 스크립트
```

## 노드와 서비스

| 항목 | 값 |
| --- | --- |
| master | `10.10.10.10` |
| worker1 | `10.10.10.11` |
| worker2 | `10.10.10.12` |
| K3s | `v1.34.6+k3s1` |
| ArgoCD | `http://10.10.10.200` |
| Longhorn | `http://10.10.10.201` |
| Grafana | `http://10.10.10.202` |

## GitOps 구조

| 항목 | 값 |
| --- | --- |
| GitHub repo | `https://github.com/aegis-pi/safe-edge-config-main.git` |
| repo path | `monitoring/`, `ai-apps/` |
| Aegis-pi reference | `docs/ops/06_argocd_gitops.md` |
| monitoring app | `safe-edge-monitoring` |
| ai app | `safe-edge-ai-apps` |

구성 원칙:

- ArgoCD 설치는 Helm으로 한다.
- GitHub repo 등록과 sync는 ArgoCD UI에서 진행한다.
- 배포 단위는 `monitoring`과 `ai-apps`로 분리한다.
- 매니페스트 변경은 GitHub repo에 push하고 ArgoCD가 반영한다.

## 구축 순서

### 1. 노드 준비

완료 기준:

```bash
kubectl get nodes -o wide
```

정상 기준:

```text
master Ready
worker1 Ready
worker2 Ready
```

### 2. Longhorn 구성

완료 기준:

```bash
kubectl -n longhorn-system get pods
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

정상 기준:

```text
Longhorn UI 접근 가능
Volume attached / healthy
InfluxDB PVC Bound
```

### 3. ArgoCD 설치

완료 기준:

```bash
kubectl -n argocd get pods
kubectl -n argocd get svc
kubectl -n argocd get application
```

정상 기준:

```text
ArgoCD UI 접근 가능
safe-edge-monitoring Synced / Healthy
safe-edge-ai-apps Synced / Healthy
```

### 4. monitoring 배포

포함:

```text
InfluxDB
Prometheus
Grafana
Node exporter
```

확인:

```bash
kubectl -n monitoring get pod -o wide
kubectl -n monitoring get pvc
```

### 5. ai-apps 배포

포함:

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
safe-edge-image-prepull
```

확인:

```bash
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n ai-apps get pvc
kubectl -n ai-apps get deploy safe-edge-integrated-ai -o jsonpath='{.spec.template.spec.volumes}{"\n"}'
```

정상 기준:

```text
bme280-sensor: worker2 Running
safe-edge-integrated-ai: worker2 Running
safe-edge-audio: worker2 Running
safe-edge-image-prepull: worker1, worker2 Running
ai-apps PVC: 없음
safe-edge-integrated-ai snapshot-storage: /var/lib/safe-edge/snapshots hostPath
```

### 6. InfluxDB 보존 정책

정책:

```text
safe_edge_db autogen retention: 1d
```

확인:

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -execute 'SHOW RETENTION POLICIES ON safe_edge_db'
```

### 7. Grafana dashboard

구성:

```text
InfluxDB datasource: 센서/AI/소리 시계열
Prometheus datasource: Node Exporter Full 1860 dashboard
```

Grafana dashboard 등록은 UI에서 진행한다.

### 8. Failover / Failback

정책:

```text
worker2 preferred affinity
tolerationSeconds: 30
master OS cron 기반 Kubernetes-only failback
worker2에 대상 Pod가 이미 있으면 skip
worker1에 남은 대상 Pod만 순차 삭제
```

검증 완료:

```text
worker2 LAN 제거 테스트
worker2 전원 제거 테스트
```

상세 결과:

```text
docs/ops/09_failover_failback_test_results.md
```

## 완료 판단

`factory-a`는 다음 조건을 만족하면 기준선 완료로 판단한다.

```text
3-node K3s Ready
Longhorn healthy
ArgoCD Synced / Healthy
InfluxDB write 정상
Grafana dashboard 갱신
AI/BME280/Audio worker2 Running
worker2 장애 시 worker1 failover
worker2 복구 후 failback 성공
AI snapshot hostPath와 cleanup 정상
```

## 후속 단계

- M0 문서와 체크리스트를 실제 완료 상태로 갱신한다.
- AWS Hub EKS/VPC/namespace/ArgoCD bootstrap 기준선, foundation S3/AMP/IoT Rule, `factory-a` IoT Thing/Policy/K3s Secret, IRSA S3/AMP 권한은 M1에서 검증했고 2026-05-06 `build-all`로 재생성되어 active 상태다. `factory-b`, `factory-c`와 Hub Prometheus/Agent 실제 AMP remote_write는 후속 확장 단계에서 진행한다.
