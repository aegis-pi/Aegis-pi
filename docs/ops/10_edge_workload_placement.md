# Edge Workload Placement

상태: source of truth
기준일: 2026-04-29

## 목적

`factory-a` Safe-Edge의 master, worker1, worker2 역할과 주요 파드 배치 기준을 정리한다. 기준은 현재 CPU/Memory 사용률, failover 여유, control-plane 안정성, edge 현장 처리 적합성이다.

## 결론

```text
master:
  Kubernetes control-plane
  CoreDNS, metrics-server, Traefik, Longhorn 필수 구성
  Grafana

worker1:
  ArgoCD
  Prometheus
  InfluxDB
  Longhorn UI 및 운영 파드

worker2:
  AI
  audio
  BME280 sensor
```

ArgoCD는 worker1에 유지한다. ArgoCD는 Git 변경을 감지하고 Kubernetes API에 원하는 상태를 요청하는 GitOps controller이며, 실제 Deployment 갱신과 Pod 생성은 master의 control-plane이 수행한다. 따라서 ArgoCD가 worker에 있어도 배포 흐름은 정상이다.

Grafana는 master로 이동한다. Grafana는 관측 UI이며 데이터 수집 경로의 핵심 처리 파드가 아니므로 worker1에서 분리해도 운영 위험이 낮다. worker1의 failover 여유를 확보하는 효과가 있다.

Grafana와 InfluxDB는 Longhorn RWO PVC를 사용하므로 Deployment 전략을 `Recreate`로 둔다. 기본 RollingUpdate는 새 Pod가 다른 노드에서 먼저 뜨면서 기존 Pod가 잡고 있는 RWO volume 때문에 Multi-Attach 대기가 발생할 수 있다.

## 기준 사용률

2026-04-29 리소스 제한과 배치 정책 적용 후 기준이다.

```text
master   158m CPU / 3%    2767Mi / 4147Mi = 68%
worker1  118m CPU / 2%    3277Mi / 8256Mi = 40%
worker2  499m CPU / 12%   4043Mi / 8256Mi = 50%
```

worker1의 주요 파드 사용량은 다음과 같다.

```text
ArgoCD 전체             worker1
Prometheus              3m CPU    255Mi
InfluxDB                6m CPU    139Mi
kube-state-metrics      2m CPU     77Mi
MetalLB controller      1m CPU     73Mi
Longhorn worker1 구성   약 60m    약 840Mi
```

worker2의 AI/audio/BME가 worker1로 failover될 경우 관측 기준 추가 부하는 약 `420m CPU`, `2.6GiB memory`다.

## 배치 판단

### ArgoCD

ArgoCD는 worker1에 유지한다.

이유:

- ArgoCD 장애는 GitOps sync 지연이지 기존 runtime 중단이 아니다.
- master는 4GiB 메모리 노드이며 `k3s-server`가 1GiB 이상 사용한다.
- ArgoCD 전체를 master로 이동하면 master 메모리가 90% 전후로 올라갈 수 있다.
- edge 처리 파드와 control-plane을 분리하는 것이 운영 안정성에 더 유리하다.

적용 기준:

```text
Helm release: argocd
namespace: argocd
chart: argo/argo-cd 9.5.4
nodeAffinity: worker1 required
```

배포 흐름:

```text
GitHub
  -> ArgoCD pod(worker1)
  -> kube-apiserver(master)
  -> scheduler/controller-manager(master)
  -> kubelet(worker1/worker2)
  -> container start/stop
```

### Grafana

Grafana는 master에 배치한다.

이유:

- worker1에서 약 460Mi 메모리를 줄일 수 있다.
- Grafana가 중단되어도 InfluxDB, Prometheus, AI, sensor 데이터 수집은 계속된다.
- master에는 반드시 request/limit을 걸어 control-plane 압박을 제한한다.

적용 기준:

```text
nodeAffinity: master required
tolerations:
  node-role.kubernetes.io/control-plane=true:NoSchedule
  node-role.kubernetes.io/master=true:NoSchedule
resources:
  requests: 100m / 256Mi
  limits:   500m / 768Mi
strategy: Recreate
```

### Prometheus

Prometheus는 worker1에 유지한다.

이유:

- 현재는 약 255Mi지만 scrape 대상과 보존 기간이 늘면 메모리가 증가할 수 있다.
- 시계열 수집기는 master보다 worker에서 운영하는 편이 적합하다.
- worker1을 운영/관측 노드로 유지하는 구조와 맞는다.

적용 기준:

```text
resources:
  requests: 100m / 256Mi
  limits:   500m / 768Mi
```

### InfluxDB

InfluxDB는 worker1에 유지한다.

이유:

- worker2의 AI/audio/sensor와 같은 장애 도메인에 두면 데이터 생산과 저장이 동시에 영향을 받을 수 있다.
- Longhorn PVC를 사용하므로 노드 장애 시 복구 가능성을 확보한다.
- 현재 메모리 사용량은 낮지만 센서 데이터 증가와 IO를 고려해 limit을 둔다.

적용 기준:

```text
resources:
  requests: 100m / 256Mi
  limits:   1000m / 768Mi
strategy: Recreate
```

### AI/audio/BME

AI, audio, BME280 sensor는 worker2 우선 배치를 유지한다.

이유:

- edge 현장 처리 workload이므로 센서/장치 접근과 함께 worker2에 집중한다.
- worker2 장애 시 worker1로 failover될 수 있도록 toleration과 image prepull을 유지한다.
- requests/limits를 적용해 failover 시 worker1 수용 가능성을 scheduler가 계산할 수 있게 한다.

적용 기준:

```text
safe-edge-integrated-ai:
  requests: 500m / 1500Mi
  limits:   2000m / 2000Mi
  strategy: Recreate

safe-edge-audio:
  requests: 100m / 1500Mi
  limits:   1000m / 2000Mi
  strategy: Recreate

bme280-sensor:
  requests: 50m / 64Mi
  limits:   200m / 256Mi
  strategy: Recreate
```

AI, audio, BME280 sensor는 하드웨어 장치를 직접 잡으므로 기본 `RollingUpdate`를 사용하지 않는다. 새 Pod와 기존 Pod가 동시에 떠서 `/dev`, `/dev/snd`, `/dev/i2c-1` 접근이 겹치지 않도록 `Recreate`로 둔다.

### AI Snapshot 저장과 Failover

`safe-edge-integrated-ai`는 추론 결과를 InfluxDB에 기록한다. InfluxDB PVC는 Longhorn을 사용하므로 위험도/탐지 결과는 InfluxDB를 통해 Longhorn에 저장된다.

반면 snapshot 이미지는 AI Pod failover를 막지 않도록 Longhorn RWO PVC를 사용하지 않는다.

```text
/app/snapshots -> node-local hostPath /var/lib/safe-edge/snapshots
```

이전 `safe-edge-ai-snapshots` Longhorn RWO PVC 방식은 `worker2` 장애 시 stale Pod/VolumeAttachment 때문에 AI가 `worker1`에서 `ContainerCreating`에 머무는 문제가 있었다. 현재 운영 구성에서는 해당 PVC와 worker2 watchdog fencing을 제거했다.

AI/audio/BME에는 Downward API로 pod identity를 주입한다.

```text
NODE_NAME = spec.nodeName
POD_NAME = metadata.name
POD_UID = metadata.uid
```

이는 후속 `event_id`, `sequence`, cloud idempotency 적용을 위한 기반이다.

## ArgoCD Resource 기준

ArgoCD는 Helm release로 설치되어 있으며 `safe-edge-config-main` GitOps repository에 직접 포함하지 않는다. 운영 중에는 Helm values로 resource 기준을 유지한다.

권장 기준:

```text
application-controller:
  requests: 100m / 256Mi
  limits:   500m / 512Mi

repo-server:
  requests: 100m / 128Mi
  limits:   500m / 512Mi

server:
  requests: 50m / 128Mi
  limits:   300m / 384Mi

dex-server:
  requests: 50m / 128Mi
  limits:   300m / 384Mi

redis:
  requests: 50m / 64Mi
  limits:   300m / 256Mi

applicationset-controller:
  requests: 50m / 64Mi
  limits:   300m / 256Mi

notifications-controller:
  requests: 25m / 64Mi
  limits:   200m / 256Mi
```

## Edge Agent 배치 계획

`edge-agent`는 현재 운영 중인 workload가 아니라 후속 클라우드 송신 컴포넌트다. 초기에는 기존 Safe-Edge workload를 대체하지 않고 `bme280-sensor`, `safe-edge-integrated-ai`, `safe-edge-audio` 옆에 추가한다.

배치 기준:

```text
namespace: ai-apps
replicas: 1
preferred: worker2
failover: worker1
avoid: master
```

Resource 기준:

```text
requests: 50m CPU / 128Mi memory
limits:   200m CPU / 256Mi memory
expected steady memory: 60~150Mi
target peak memory: 200Mi 이하
strategy: Recreate for MVP
```

초기 데이터 수집 방식:

```text
edge-agent
  -> InfluxDB query
  -> Kubernetes API status query
  -> AWS IoT Core MQTT publish
```

초기에는 `/dev/i2c-1`, camera, mic 같은 장치를 직접 잡지 않는다. 따라서 AI/audio/BME처럼 하드웨어 충돌 때문에 `Recreate`가 필수인 것은 아니지만, 중복 publish를 피하기 위해 MVP에서는 1 replica를 유지하고 rolling update 동작은 별도 검증 후 확정한다.

송신 안정성 기준:

```text
message_id idempotency key 필수
last sent checkpoint 필수
MQTT QoS 1 권장
reconnect/backoff 필수
cluster-admin 금지, 최소 RBAC 사용
AWS IoT certificate/private key는 Kubernetes Secret으로만 주입
```

상세 계획은 `docs/planning/06_edge_agent_deployment_plan.md`를 기준으로 한다.

## 검증

적용 후 다음 명령으로 확인한다.

```bash
kubectl get pod -A -o wide
kubectl top nodes
kubectl -n monitoring top pod --containers
kubectl -n ai-apps top pod --containers
kubectl -n argocd top pod --containers
kubectl -n monitoring get pod -l app=grafana -o wide
kubectl -n argocd get pod -o wide
```

정상 기준:

```text
Grafana: master
ArgoCD: worker1
Prometheus: worker1
InfluxDB: worker1
AI/audio/BME: worker2
```

## 운영 주의

- master는 control-plane 노드이므로 Grafana 외 추가 workload를 신중하게 제한한다.
- master에 배치하는 workload에는 반드시 resource limit을 둔다.
- ArgoCD가 worker1에 있어도 Kubernetes 배포 제어권은 master의 API server와 controller-manager에 있다.
- GitOps repo에 반영한 뒤 ArgoCD Application revision과 sync 상태를 확인한다.
