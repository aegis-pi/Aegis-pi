# Edge Agent 배포 계획

상태: draft
기준일: 2026-04-29

## 목적

클라우드 확장을 위해 새로 만들 `edge-agent` 이미지와 K3s 배포 방식을 정리한다.

`edge-agent`는 기존 Safe-Edge 워크로드를 대체하는 것이 아니라, 초기에는 기존 `bme280-sensor`, `safe-edge-integrated-ai`, `safe-edge-audio` 옆에 추가되는 클라우드 송신 컴포넌트다.

## 역할

`edge-agent`는 `factory-a`의 로컬 데이터와 상태를 표준 입력 스키마로 변환하고 AWS IoT Core로 전송한다.

```text
existing workloads
  - bme280-sensor
  - safe-edge-integrated-ai
  - safe-edge-audio

edge-agent
  -> collect latest local data/status
  -> build standard schema
  -> MQTT publish to AWS IoT Core
```

## 왜 새 이미지가 필요한가

현재 `factory-a`에는 로컬 관제용 워크로드가 있다.

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
InfluxDB
Grafana
Prometheus
```

하지만 클라우드 확장을 위해 필요한 기능은 별도다.

```text
local data/status 수집
표준 스키마 변환
AWS IoT Core 인증서 기반 MQTT 연결
factory_id / node_id / source_type 포함 메시지 발행
중복 publish 방지를 위한 idempotency key 생성
last sent checkpoint 관리
연결 끊김 시 재연결
health/log 제공
```

따라서 `apps/edge-agent`에서 별도 이미지를 만들고, ECR에 push한 뒤 K3s에 Deployment로 배포한다.

## 권장 구현 방식

MVP에서는 `edge-agent` 하나를 만들고 설정으로 real/dummy mode를 나누는 방식을 권장한다.

```text
factory-a:
  image: edge-agent
  mode: real
  environment_type: physical-rpi
  input_module_type: sensor

factory-b:
  image: edge-agent
  mode: dummy
  environment_type: vm-mac
  input_module_type: dummy

factory-c:
  image: edge-agent
  mode: dummy
  environment_type: vm-windows
  input_module_type: dummy
```

이 방식은 표준 스키마 생성과 AWS IoT Core 송신 로직을 하나의 코드에서 공유할 수 있다.

## 데이터 수집 방식

초기에는 `edge-agent`가 센서 장치를 직접 읽지 않는다.

권장 초기 구조:

```text
bme280-sensor -> InfluxDB
safe-edge-integrated-ai -> InfluxDB / snapshot
safe-edge-audio -> InfluxDB

edge-agent
  -> InfluxDB query
  -> Kubernetes API status query
  -> checkpoint 기준 미전송 데이터 선별
  -> idempotency key 포함 표준 payload 생성
  -> AWS IoT Core publish
```

이유:

- `/dev/i2c-1`, camera, mic 같은 장치 직접 접근을 피할 수 있다.
- worker2 장애 후 worker1로 failover되어도 InfluxDB/Kubernetes API 기반 상태 전송을 유지할 수 있다.
- 기존 M0 Safe-Edge 기준선을 크게 흔들지 않는다.
- 장치 수집 책임과 클라우드 송신 책임을 분리할 수 있다.

후속 단계에서 필요하면 직접 장치 접근을 추가한다.

## 송신 안정성 기준

`edge-agent`는 단순 MQTT forwarder가 아니라 재시작, failover, 네트워크 단절 중에도 중복과 누락을 제어하는 edge sender로 구현한다.

### Idempotency key

모든 메시지는 수신 측에서 중복 제거가 가능하도록 고정 key를 포함한다.

권장 필드:

```json
{
  "message_id": "factory-a:environment_data:2026-04-29T03:00:00.000Z",
  "factory_id": "factory-a",
  "node_id": "worker2",
  "source_type": "sensor",
  "measurement": "environment_data",
  "source_timestamp": "2026-04-29T03:00:00.000Z",
  "published_at": "2026-04-29T03:00:01.234Z",
  "agent_instance_id": "edge-agent-abc123"
}
```

`message_id`는 같은 원본 데이터에 대해 항상 같은 값이 나오도록 만든다. MVP에서는 아래 조합을 기본으로 한다.

```text
factory_id + measurement/source_type + source_timestamp
```

AI 이벤트처럼 동일 timestamp에 여러 이벤트가 생길 수 있으면 `event_id` 또는 원본 row hash를 추가한다.

현재 `factory-a` 운영 워크로드에는 `NODE_NAME`, `POD_NAME`, `POD_UID` Downward API 환경변수를 주입해 두었다. 이는 AI/audio/BME 이미지가 원본 이벤트에 `event_id`, `node_id`, `pod_uid`, `sequence`를 넣기 위한 전제 조건이다.

권장 원본 이벤트 key:

```text
event_id = source_type + pod_uid + session_id + sequence
```

예시:

```text
bme280:9c2a...:20260429T145300Z:00000123
ai:7f5b...:20260429T145300Z:00000045
audio:aa81...:20260429T145300Z:00000210
```

남은 작업:

```text
AI/audio/BME 이미지 소스에서 session_id 생성
measurement별 sequence 증가
InfluxDB write payload에 event_id, node_id, pod_name, pod_uid, sequence 추가
edge-agent는 event_id를 IoT Core message_id로 사용
```

### Checkpoint

`edge-agent`는 마지막으로 성공 publish한 위치를 기록한다.

권장 checkpoint:

```text
last_sent_timestamp
last_sent_measurement
last_sent_source_type
last_successful_publish_at
```

MVP 저장 위치는 다음 순서로 검토한다.

```text
1. InfluxDB marker measurement
2. 작은 Longhorn PVC 파일
3. 메모리 only
```

권장 초기값은 InfluxDB marker measurement다. 이유는 InfluxDB가 이미 로컬 데이터 기준점이며, worker2에서 worker1로 failover되어도 같은 checkpoint를 조회할 수 있기 때문이다.

```text
measurement: edge_agent_checkpoint
fields:
  last_sent_timestamp
  last_successful_publish_at
tags:
  factory_id
  source_type
  measurement
```

메모리 only checkpoint는 재시작 시 최근 데이터를 다시 보낼 수 있으므로 데모용 초기 smoke test에만 허용한다.

### 재연결과 backoff

AWS IoT Core 연결이 끊기면 즉시 무한 재시도를 하지 않는다.

권장 기준:

```text
initial backoff: 1s
max backoff: 60s
jitter: enabled
offline queue: memory bounded
queue overflow policy: oldest drop 또는 publish skip metric 증가
```

MVP에서는 offline queue를 작게 유지한다. 장시간 단절 구간은 InfluxDB checkpoint 기반 재조회로 복구하고, 메모리에 모든 데이터를 쌓지 않는다.

### Publish QoS

MVP 기본값은 MQTT QoS 1을 권장한다.

```text
QoS 0: 빠르지만 유실 가능
QoS 1: 최소 1회 전달, 중복 가능
QoS 2: 복잡도 증가
```

QoS 1은 중복 가능성이 있으므로 idempotency key와 S3 object key 설계를 함께 적용한다.

## AWS IoT Core 연결

Thing 등록은 AWS IoT Core에서 공장 단위로 한다.

```text
Thing:
  aegis-factory-a
  aegis-factory-b
  aegis-factory-c
```

K3s에는 Thing 자체를 등록하지 않는다. K3s에는 해당 Thing의 인증서를 Kubernetes Secret으로 배포한다.

```text
AWS IoT Core:
  Thing
  Certificate
  Policy
  Thing <-> Certificate attachment

K3s:
  Secret
  ConfigMap
  edge-agent Deployment
```

K3s Secret 예시:

```bash
kubectl -n ai-apps create secret generic aws-iot-factory-a-cert \
  --from-file=certificate.pem.crt=factory-a.cert.pem \
  --from-file=private.pem.key=factory-a.private.key \
  --from-file=AmazonRootCA1.pem=AmazonRootCA1.pem
```

주의:

```text
AWS IoT 인증서와 private key는 Git repository에 커밋하지 않는다.
MVP에서는 kubectl create secret으로 수동 주입한다.
후속 운영에서는 SealedSecrets, External Secrets Operator, SOPS 중 하나를 검토한다.
```

Pod 환경변수 예시:

```yaml
env:
  - name: AWS_IOT_CLIENT_ID
    value: aegis-factory-a
  - name: FACTORY_ID
    value: factory-a
  - name: AWS_IOT_TOPIC_PREFIX
    value: aegis/factory-a
  - name: ENVIRONMENT_TYPE
    value: physical-rpi
  - name: INPUT_MODULE_TYPE
    value: sensor
  - name: EDGE_AGENT_MODE
    value: real
  - name: EDGE_AGENT_QOS
    value: "1"
  - name: EDGE_AGENT_CHECKPOINT_BACKEND
    value: influxdb
```

인증서는 Secret volume으로 mount한다.

```yaml
volumeMounts:
  - name: aws-iot-cert
    mountPath: /etc/aegis/iot
    readOnly: true
volumes:
  - name: aws-iot-cert
    secret:
      secretName: aws-iot-factory-a-cert
```

## 예상 리소스

`edge-agent`는 가벼운 Python 또는 Go 계열 송신 파드로 설계한다.

초기 구현은 Python을 권장한다. 라즈베리파이 상태 수집, InfluxDB query, Kubernetes API 연동, MQTT 송신 구현이 빠르기 때문이다.

권장 resource:

| 항목 | 값 |
| --- | --- |
| CPU request | `50m` |
| CPU limit | `200m` |
| Memory request | `128Mi` |
| Memory limit | `256Mi` |
| 평상시 예상 메모리 | `60~150Mi` |
| 피크 예상 메모리 | `200Mi` 이하 목표 |

Kubernetes 예시:

```yaml
resources:
  requests:
    cpu: 50m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi
```

리소스 기준은 실제 파드 배포 후 `kubectl top pod` 결과로 보정한다.

## 노드 배치

`factory-a`에서는 worker2 우선 배치를 사용한다.

```text
preferred: worker2
failover: worker1
avoid: master
```

이유:

- worker2는 현재 sensor / AI / audio preferred 노드다.
- edge-agent는 edge 입력과 가까운 workload다.
- worker2 장애 시 worker1에서 상태 전송을 이어갈 수 있어야 한다.
- master는 control-plane 노드이며 메모리 여유가 작으므로 데이터 송신 파드 배치를 피한다.

평상시 배치:

```text
worker2:
  bme280-sensor
  safe-edge-integrated-ai
  safe-edge-audio
  edge-agent
```

장애 시:

```text
worker2 NotReady
  -> edge-agent worker1로 재스케줄
  -> InfluxDB/Kubernetes API 기반 system_status 또는 pipeline 관련 상태 송신
```

## Affinity / Toleration 기준

`edge-agent`는 기존 AI/audio/BME 계열과 같은 장애 전환 철학을 따른다.

권장 toleration:

```yaml
tolerations:
  - key: node.kubernetes.io/not-ready
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 30
  - key: node.kubernetes.io/unreachable
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 30
```

권장 node affinity:

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: aegis.node-role
              operator: In
              values:
                - sensor-ai
      - weight: 50
        preference:
          matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - worker2
```

노드 라벨은 후속 배포 전 실제 값으로 확정한다.

예시:

```bash
kubectl label node worker2 aegis.node-role=sensor-ai
kubectl label node worker1 aegis.node-role=failover-standby
```

## Namespace

초기에는 기존 `ai-apps` namespace에 둔다.

이유:

- `edge-agent`가 기존 AI/audio/BME workload와 같은 edge application 범주에 있다.
- M0 기준선의 namespace 수를 불필요하게 늘리지 않는다.
- 기존 failover 관측과 운영 문서에 통합하기 쉽다.

후속 Hub 확장과 역할 분리가 커지면 `edge-system` namespace를 검토한다.

```text
MVP:
  ai-apps

후속 후보:
  edge-system
```

## Kubernetes API 권한

`edge-agent`가 Kubernetes 상태를 읽으려면 ServiceAccount와 RBAC를 별도로 둔다. `cluster-admin`은 사용하지 않는다.

초기 권한 범위:

```text
resources:
  pods
  nodes
  deployments

verbs:
  get
  list
  watch
```

초기 구현에서는 `ai-apps`, `monitoring` namespace의 Pod/Deployment 상태를 우선 읽고, node 상태만 cluster scope로 읽는다.

예시:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: edge-agent
  namespace: ai-apps
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: edge-agent-read
rules:
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
```

실제 배포 전에는 필요한 리소스가 더 좁혀지는지 확인하고 Role/RoleBinding으로 namespace scope를 우선 적용한다.

## 배포 리소스

초기 배포 리소스 후보:

```text
ConfigMap:
  edge-agent-config

Secret:
  aws-iot-factory-a-cert

ServiceAccount / RBAC:
  edge-agent
  edge-agent-read

Deployment:
  edge-agent

Service:
  edge-agent-metrics 또는 health endpoint가 필요할 때만 추가
```

Deployment는 1 replica로 시작한다.

```text
replicas: 1
```

중복 publish 위험이 있으므로 active-active 복제는 MVP에서 하지 않는다.

Deployment update 전략은 초기에는 `Recreate`를 권장한다. `edge-agent`가 직접 하드웨어를 잡지는 않지만, 1 replica 송신기에서 RollingUpdate가 발생하면 짧은 시간 동안 두 sender가 동시에 동작할 수 있다. idempotency key와 checkpoint가 충분히 검증된 뒤 RollingUpdate 전환을 검토한다.

## Topic 기준

초기 topic:

```text
aegis/factory-a/sensor
aegis/factory-a/system_status
aegis/factory-b/sensor
aegis/factory-b/system_status
aegis/factory-c/sensor
aegis/factory-c/system_status
```

payload에는 반드시 `message_id`, `factory_id`, `node_id`, `source_type`, `source_timestamp`, `published_at`을 포함한다.

노드 구분은 IoT Thing을 나누지 않고 payload의 `node_id`로 표현한다.

S3 object key는 중복 처리가 가능하도록 `message_id` 또는 그 hash를 포함한다.

예시:

```text
s3://<bucket>/factory_id=factory-a/source_type=sensor/date=2026-04-29/<message_id>.json
```

## 구현 산출물

후속 구현 시 필요한 파일:

```text
apps/edge-agent/
  Dockerfile
  source code
  README.md

charts/aegis-spoke/
  templates/edge-agent-deployment.yaml
  templates/edge-agent-configmap.yaml
  templates/edge-agent-rbac.yaml
  templates/edge-agent-secret-example.yaml 또는 문서화

envs/factory-a/values.yaml
envs/factory-b/values.yaml
envs/factory-c/values.yaml
```

## 검증 기준

초기 검증:

```text
[ ] edge-agent 이미지 ARM64 빌드 성공
[ ] ECR push 성공
[ ] factory-a K3s에서 edge-agent Pod Running
[ ] AWS IoT Core MQTT test client에서 메시지 수신
[ ] message_id가 같은 원본 데이터에 대해 안정적으로 생성됨
[ ] 재시작 후 checkpoint 기준으로 중복 송신이 제한됨
[ ] S3에 factory-a/sensor 경로 적재
[ ] S3에 factory-a/system_status 경로 적재
[ ] S3 object key에 message_id 또는 hash가 포함됨
[ ] worker2 장애 시 edge-agent worker1 재스케줄 확인
[ ] 재스케줄 후 system_status 또는 pipeline 관련 상태 송신 확인
[ ] AWS IoT Core 연결 단절 후 backoff 재연결 확인
```

리소스 검증:

```text
[ ] 평상시 메모리 150Mi 이하
[ ] 피크 메모리 200Mi 이하
[ ] CPU request 50m 기준으로 안정 동작
[ ] worker1 failover 시 기존 AI/audio/BME와 함께 수용 가능
```

## 열린 결정 사항

```text
[ ] 구현 언어 최종 결정: Python 또는 Go
[ ] InfluxDB query 방식: 직접 HTTP API 또는 influx CLI/API client
[ ] checkpoint 저장 위치: InfluxDB marker measurement 또는 Longhorn PVC
[ ] S3 object key 최종 규칙
[ ] edge-agent health endpoint 필요 여부
[ ] metrics endpoint 제공 여부
[ ] offline queue overflow 정책: oldest drop 또는 publish skip
[ ] `ai-apps` 유지 또는 `edge-system` namespace 분리 시점
[ ] worker2 라벨명 최종 확정
```

## 결론

MVP에서는 `edge-agent`를 새 이미지로 만들고 `factory-a` K3s에 1 replica Deployment로 추가한다.

기본 배치는 worker2 preferred, worker1 failover, master avoid로 둔다.

초기 리소스 기준은 아래와 같다.

```text
requests: 50m CPU / 128Mi memory
limits:   200m CPU / 256Mi memory
```

초기 데이터 소스는 직접 장치 접근이 아니라 InfluxDB와 Kubernetes API를 사용한다.

구현 시 반드시 포함할 운영 기준은 아래 네 가지다.

```text
idempotency key
last sent checkpoint
MQTT reconnect/backoff
minimum RBAC + Secret 분리
```
