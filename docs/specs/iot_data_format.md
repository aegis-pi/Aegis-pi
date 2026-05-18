# IoT Core Data Format

상태: source of truth
기준일: 2026-05-18

## 목적

이 문서는 Edge data-plane components가 AWS IoT Core로 전송할 canonical JSON 데이터 포맷을 확정한다.

이 포맷은 아래 요구사항을 만족하기 위해 만든다.

- Risk Score 계산에 필요한 공장 상태 값을 3초 단위로 제공한다.
- 클러스터, 노드, 워크로드, 장치, 파이프라인 상태를 20초 단위로 제공한다.
- AI 모델의 순간 오탐에 민감하게 반응하지 않도록 최근 window 평균값을 보낸다.
- IoT Core topic과 S3 raw partition을 단순하게 유지한다.
- Edge data-plane은 원본 사실과 요약값만 보내고, 최종 위험 판단은 cloud-side Lambda data processor가 수행한다.
- `pipeline_status`는 Edge가 직접 보내지 않고 cloud-side에서 계산한다.

2026-05-15 기준 Edge side 책임은 아래처럼 분리한다.

```text
factory-a-log-adapter
  -> canonical JSON
  -> local spool/outbox

dummy-data-generator
  -> canonical JSON
  -> local spool/outbox

edge-iot-publisher
  -> AWS IoT Core
```

## 확정 과정

초기안은 `sensor`, `ai_result`, `node_status`, `workload_status`, `device_status`, `pipeline_heartbeat`를 각각 별도 `source_type`으로 전송하는 구조였다.

검토 중 아래 판단을 반영했다.

1. Risk Score에 직접 필요한 값은 온도, 습도, 기압, AI 결과이므로 하나의 공장 상태 메시지로 묶는 편이 계산이 단순하다.
2. AI 파드는 내부에서 1초 단위로 동작하더라도 모델 성능이 아직 안정적이지 않으므로 상태 변화 즉시 이벤트를 보내면 오탐 민감도가 높아진다.
3. AI의 `0/1` 결과를 Edge에서 최종 판정하지 않고, 최근 N개 또는 최근 3초 window의 평균 score로 보내면 Lambda data processor의 Risk 계산 로직에서 가중치를 곱해 쓰기 쉽다.
4. 노드/워크로드/장치/heartbeat는 Risk Score 입력보다 운영 상태 확인 목적이 강하므로 20초 주기로 충분하다.
5. `pipeline_heartbeat`를 별도 topic으로 두면 운영 부담이 늘어나므로 `infra_state.payload.heartbeat`에 포함한다.

따라서 최종 source type은 아래 두 개로 확정한다.

```text
factory_state
infra_state
```

## 전체 구조

```text
factory-a-log-adapter / dummy-data-generator
  -> factory_state every 3s
  -> infra_state every 20s
  -> local spool/outbox
  -> edge-iot-publisher
  -> AWS IoT Core
      -> IoT Rule -> S3 raw
      -> Lambda data processor -> DynamoDB LATEST/HISTORY + S3 processed

Dashboard API/Web
  -> DynamoDB LATEST/HISTORY
  -> S3 processed
```

## MQTT Topic

Topic 형식:

```text
aegis/{factory_id}/{source_type}
```

사용 topic:

```text
aegis/factory-a/factory_state
aegis/factory-a/infra_state
```

후속 `factory-b`, `factory-c`도 같은 규칙을 사용한다.

```text
aegis/factory-b/factory_state
aegis/factory-b/infra_state
aegis/factory-c/factory_state
aegis/factory-c/infra_state
```

## S3 Raw Path

IoT Rule은 수신 메시지를 아래 경로로 저장한다.

```text
raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
```

예시:

```text
raw/factory-a/factory_state/yyyy=2026/mm=05/dd=14/factory-a:factory_state:worker2:2026-05-14T01:00:00Z.json
raw/factory-a/infra_state/yyyy=2026/mm=05/dd=14/factory-a:infra_state:cluster:2026-05-14T01:00:00Z.json
```

## Common Envelope

모든 메시지는 같은 envelope를 사용한다.

```json
{
  "schema_version": "0.1.0",
  "message_id": "factory-a:factory_state:worker2:2026-05-14T01:00:00Z",
  "factory_id": "factory-a",
  "node_id": "worker2",
  "environment_type": "physical-rpi",
  "input_module_type": "sensor",
  "source_type": "factory_state",
  "source_timestamp": "2026-05-14T01:00:00Z",
  "published_at": "2026-05-14T01:00:01Z",
  "data_plane_instance_id": "edge-iot-publisher-7f8c9d",
  "payload": {}
}
```

필드 기준:

| 필드 | 설명 |
| --- | --- |
| `schema_version` | 메시지 스키마 버전 |
| `message_id` | 중복 저장/재처리를 막기 위한 idempotency key |
| `factory_id` | 공장 ID |
| `node_id` | 메시지 기준 노드. 클러스터 요약이면 `cluster` |
| `environment_type` | `physical-rpi`, `vm-mac`, `vm-windows` |
| `input_module_type` | `sensor` 또는 `dummy` |
| `source_type` | `factory_state` 또는 `infra_state` |
| `source_timestamp` | 원본 데이터 기준 시각, UTC ISO 8601 |
| `published_at` | IoT Core publish 시각, UTC ISO 8601 |
| `data_plane_instance_id` | 메시지를 최종 작성 또는 publish한 Edge data-plane component 인스턴스 식별자 |
| `payload` | source type별 본문 |

### Envelope Contract

M4 구현에서는 위 envelope 필드를 모두 필수로 보낸다. 필드가 없으면 Lambda data processor는 해당 메시지를 처리 실패로 기록하고 DynamoDB LATEST/HISTORY에는 반영하지 않는다.

허용값:

| 필드 | 허용값 |
| --- | --- |
| `schema_version` | `0.1.0` |
| `factory_id` | `factory-a`, `factory-b`, `factory-c` |
| `node_id` | `master`, `worker1`, `worker2`, `cluster`, 또는 VM 단일 노드 ID |
| `environment_type` | `physical-rpi`, `vm-mac`, `vm-windows` |
| `input_module_type` | `sensor`, `dummy` |
| `source_type` | `factory_state`, `infra_state` |

`message_id` 형식은 아래 기준을 따른다.

```text
{factory_id}:{source_type}:{node_id}:{source_timestamp}
```

예시:

```text
factory-a:factory_state:worker2:2026-05-14T01:00:00Z
factory-a:infra_state:cluster:2026-05-14T01:00:00Z
```

`factory-a-log-adapter` 또는 `dummy-data-generator`가 `message_id`, `source_timestamp`, `factory_id`, `node_id`, `environment_type`, `input_module_type`, `source_type`, `payload`를 만든다. `edge-iot-publisher`는 IoT Core publish 직전에 `published_at`과 `data_plane_instance_id`를 채워 보낸다. 이미 값이 있더라도 실제 publish 시각 기준으로 `published_at`은 publisher가 덮어쓴다.

## factory_state

`factory_state`는 Risk Score 계산용 데이터다.

전송 주기:

```text
3초
```

포함 데이터:

- 온도 평균
- 습도 평균
- 기압 평균
- 화재 score
- 넘어짐 score
- 굽힘 score
- 이상소음 대표 라벨

센서값은 최근 3초 또는 최근 N개 샘플 평균값으로 보낸다. AI 결과는 최근 N개 추론 결과의 평균값으로 보낸다.

예를 들어 최근 3개 fall 결과가 `0, 1, 1`이면 아래처럼 보낸다.

```text
fall_score = 0.6667
```

Edge data-plane은 `fall_detected = 1` 같은 최종 판정을 만들지 않는다. 최종 threshold와 위험 등급은 Lambda data processor의 Risk 계산 로직이 결정한다.

`abnormal_sound`는 M4 Issue 2 초기 구현에서 기존 스키마 호환성을 위해 문자열 필드로 유지한다. 실제 `factory-a` InfluxDB의 `acoustic_detection` measurement는 `confidence`/`is_danger` field와 `event_type`/`location`/`node` tag를 가진다.

adapter는 최근 3초 window에서 `acoustic_detection`을 집계한다. `sum(is_danger) > 0`이면 대표 `event_type`을 `abnormal_sound`에 넣고, 대표 라벨이 없거나 `None`이면 `"abnormal_sound"`를 넣는다. `sum(is_danger) == 0`이거나 샘플이 없으면 `"none"`을 넣는다. `confidence`는 현재 canonical schema에 별도 필드로 보내지 않고, 후속 스키마 보정 시 `audio_result` 같은 구조로 확장할 수 있다.

예시 메시지:

```json
{
  "schema_version": "0.1.0",
  "message_id": "factory-a:factory_state:worker2:2026-05-14T01:00:00Z",
  "factory_id": "factory-a",
  "node_id": "worker2",
  "environment_type": "physical-rpi",
  "input_module_type": "sensor",
  "source_type": "factory_state",
  "source_timestamp": "2026-05-14T01:00:00Z",
  "published_at": "2026-05-14T01:00:01Z",
  "data_plane_instance_id": "edge-iot-publisher-7f8c9d",
  "payload": {
    "aggregation_window_seconds": 3,
    "sensor": {
      "sample_count": 5,
      "temperature_celsius_avg": 24.6,
      "humidity_percent_avg": 58.1,
      "pressure_hpa_avg": 1012.7
    },
    "ai_result": {
      "sample_count": 3,
      "fire_score": 0.0,
      "fall_score": 0.6667,
      "bend_score": 0.3333,
      "abnormal_sound": "none"
    }
  }
}
```

### Risk Score 입력 필드

Lambda data processor의 Risk 계산 로직은 `factory_state.payload`의 아래 필드를 사용한다.

```text
payload.sensor.temperature_celsius_avg
payload.sensor.humidity_percent_avg
payload.sensor.pressure_hpa_avg
payload.ai_result.fire_score
payload.ai_result.fall_score
payload.ai_result.bend_score
payload.ai_result.abnormal_sound
```

Risk 계산은 아래 형태를 기본으로 한다.

```text
temperature_risk = normalized_temperature * temperature_weight
humidity_risk = normalized_humidity * humidity_weight
pressure_risk = normalized_pressure * pressure_weight
fire_risk = fire_score * fire_weight
fall_risk = fall_score * fall_weight
bend_risk = bend_score * bend_weight
abnormal_sound_risk = sound_rule_or_score * sound_weight
```

## infra_state

`infra_state`는 클러스터, 노드, 장치, 워크로드, 파이프라인 상태 확인용 데이터다.

전송 주기:

```text
20초
```

포함 데이터:

- Edge data-plane heartbeat
- 클러스터 이름과 Kubernetes 버전
- 노드 Ready 상태와 리소스 사용률
- 워크로드 Pod 상태와 배치 노드
- BME280, camera, microphone 장치 가용성

예시 메시지:

```json
{
  "schema_version": "0.1.0",
  "message_id": "factory-a:infra_state:cluster:2026-05-14T01:00:00Z",
  "factory_id": "factory-a",
  "node_id": "cluster",
  "environment_type": "physical-rpi",
  "input_module_type": "sensor",
  "source_type": "infra_state",
  "source_timestamp": "2026-05-14T01:00:00Z",
  "published_at": "2026-05-14T01:00:01Z",
  "data_plane_instance_id": "edge-iot-publisher-7f8c9d",
  "payload": {
    "heartbeat": {
      "agent_status": "alive",
      "last_successful_publish_at": "2026-05-14T01:00:01Z",
      "last_checkpoint_timestamp": "2026-05-14T01:00:00Z",
      "publish_sequence": 12345
    },
    "cluster": {
      "cluster_name": "factory-a",
      "kubernetes_version": "v1.34.6+k3s1"
    },
    "nodes": [
      {
        "node_id": "master",
        "role": "control-plane",
        "ready": true,
        "cpu_usage_percent": 31.2,
        "memory_usage_percent": 55.4,
        "disk_usage_percent": 42.1,
        "network_reachability": "ok"
      },
      {
        "node_id": "worker1",
        "role": "failover-standby",
        "ready": true,
        "cpu_usage_percent": 22.8,
        "memory_usage_percent": 48.0,
        "disk_usage_percent": 39.5,
        "network_reachability": "ok"
      },
      {
        "node_id": "worker2",
        "role": "sensor-ai-audio-preferred",
        "ready": true,
        "cpu_usage_percent": 44.8,
        "memory_usage_percent": 63.0,
        "disk_usage_percent": 45.5,
        "network_reachability": "ok"
      }
    ],
    "workloads": [
      {
        "namespace": "ai-apps",
        "name": "safe-edge-integrated-ai",
        "status": "Running",
        "ready": true,
        "restart_count": 0,
        "node_id": "worker2"
      },
      {
        "namespace": "ai-apps",
        "name": "bme280-sensor",
        "status": "Running",
        "ready": true,
        "restart_count": 0,
        "node_id": "worker2"
      }
    ],
    "devices": {
      "bme280": {
        "available": true,
        "last_seen_at": "2026-05-14T01:00:00Z"
      },
      "camera": {
        "available": true,
        "last_seen_at": "2026-05-14T01:00:00Z"
      },
      "microphone": {
        "available": true,
        "last_seen_at": "2026-05-14T01:00:00Z"
      }
    }
  }
}
```

## Pipeline Health

`pipeline_heartbeat`는 별도 MQTT topic으로 보내지 않는다. `infra_state.payload.heartbeat`에 포함한다.

Cloud-side Lambda data processor는 아래 입력을 바탕으로 `pipeline_status`를 계산한다.

- 최신 `infra_state` 수신 시각
- IoT Core 수신 시각
- S3 raw object 생성 시각
- `infra_state.payload.heartbeat.last_successful_publish_at`

기본 판단 기준:

| 상태 | 조건 |
| --- | --- |
| `normal` | latest `infra_state` age <= 20초 |
| `warning` | latest `infra_state` age > 40초 |
| `critical` | latest `infra_state` age > 60초 |

이 기준은 20초 주기에서 1분 내 파이프라인 이상을 감지하기 위한 MVP 기준이다. M7 통합 검증에서 실제 지연과 누락률을 보고 보정한다.

## Payload Size and Traffic

현재 예시 메시지를 compact JSON으로 직렬화했을 때의 대략적인 payload 크기는 아래와 같다.

| source_type | compact JSON 예시 크기 | 전송 주기 | 초당 payload | 1일 payload |
| --- | ---: | ---: | ---: | ---: |
| `factory_state` | 약 0.6 KB | 3초 | 약 0.2 KB/s | 약 18 MB/day |
| `infra_state` | 약 1.6 KB | 20초 | 약 0.08 KB/s | 약 7 MB/day |
| 합계 | - | - | 약 0.3 KB/s | 약 25 MB/day |

위 값은 JSON payload만 기준으로 한 MVP 산정값이다. MQTT/TLS, IoT Core, S3 object metadata, CloudWatch log 같은 전송/저장 오버헤드는 포함하지 않는다.

판단:

- 공장 1개 기준 raw payload는 하루 약 25 MB 수준이므로 IoT Core와 S3 적재 병목보다 처리 단순성이 더 중요하다.
- `factory_state`는 Risk Score 입력이므로 3초 주기를 유지한다.
- `infra_state`는 운영 헬스 체크 목적이므로 20초 주기로도 1분 내 이상 감지가 가능하다.
- M7 통합 검증에서 실제 payload 크기, publish 성공률, S3 적재 지연, Dashboard 반영 지연을 측정해 보정한다.

## Null and Missing Value Policy

MVP 기준 원칙:

- envelope 필드는 모두 필수이며 `null`을 허용하지 않는다.
- `payload` 하위 객체는 가능한 한 구조를 유지한다. 수집 실패 때문에 객체 자체를 삭제하지 않는다.
- 센서 값을 읽지 못한 경우에는 `payload.sensor.sample_count: 0`을 보내고 `temperature_celsius_avg`, `humidity_percent_avg`, `pressure_hpa_avg`는 `null`로 둔다.
- AI 값을 읽지 못한 경우에는 `payload.ai_result.sample_count: 0`을 보내고 `fire_score`, `fall_score`, `bend_score`는 `null`로 둔다.
- `abnormal_sound`는 정상/미감지 상태에서 `"none"`을 보낸다. acoustic event label이 감지되면 해당 `event_type` 대표 라벨을 보내고, 위험 감지는 있지만 label이 없으면 `"abnormal_sound"`를 보낸다.
- 장치가 없거나 비활성인 경우에는 `available: false`와 `last_seen_at: null`을 함께 보낸다.
- `nodes`, `workloads` 같은 배열은 조회 실패 시 빈 배열 `[]`을 보낼 수 있다.
- 개별 노드나 워크로드의 수치형 상태를 읽지 못한 경우에는 해당 값을 `null`로 둔다.
- 상태 문자열을 알 수 없으면 임의 값을 만들지 않고 `unknown`을 사용한다.
- 필드 삭제보다 명시적 `null`, `false`, `unknown`, 빈 배열을 선호한다.

## Local Spool/Outbox Contract

`factory-a-log-adapter`와 `dummy-data-generator`는 IoT Core에 직접 publish하지 않고 local spool/outbox에 canonical JSON 파일을 남긴다. `edge-iot-publisher`는 이 파일을 읽어 IoT Core로 publish한다.

기본 경로:

```text
/var/lib/aegis/outbox
/var/lib/aegis/outbox/tmp
/var/lib/aegis/outbox/quarantine
```

파일 계약:

| 항목 | 기준 |
| --- | --- |
| 파일 내용 | canonical JSON 한 건 |
| 파일명 | `{message_id}.json` |
| 임시 파일 | `{message_id}.json.tmp` |
| 문자 인코딩 | UTF-8 |
| JSON 형식 | compact 또는 pretty 모두 허용. 의미가 같아야 함 |

쓰기 원칙:

1. adapter/generator는 먼저 `tmp/`에 `{message_id}.json.tmp`로 쓴다.
2. 파일 쓰기와 flush가 끝나면 같은 filesystem 안에서 `{message_id}.json`으로 atomic rename 한다.
3. publisher는 `.json` 파일만 publish 대상으로 본다.
4. publisher는 IoT Core publish 성공을 확인한 뒤 원본 `.json` 파일을 삭제한다.
5. publish 실패, 네트워크 실패, 인증 실패가 발생하면 파일을 삭제하지 않고 다음 scan에서 재시도한다.
6. JSON parse 실패나 필수 envelope 누락은 publish하지 않고 `quarantine/`으로 이동한다.

재시도 기준:

| 상황 | 처리 |
| --- | --- |
| 일시적 네트워크 실패 | 파일 유지, exponential backoff 후 재시도 |
| IoT Core 인증 실패 | 파일 유지, 에러 로그 기록, 다음 health check에서 계속 실패 상태 노출 |
| schema validation 실패 | `quarantine/` 이동 |
| 중복 파일명 | 같은 `message_id`로 보고 새 파일을 덮어쓰지 않음 |

MVP에서는 별도 ack 파일을 만들지 않는다. 성공 기준은 IoT Core publish 성공 후 outbox 파일 삭제다. 중복 publish가 발생할 수 있으므로 cloud-side Lambda data processor는 `message_id` 기준으로 idempotent하게 처리한다.

## S3 Raw Body Contract

S3 raw object body는 IoT Core로 publish된 canonical JSON과 동일한 payload를 저장한다. IoT Rule SQL은 body에 `received_at` 같은 보조 필드를 추가하지 않고 `SELECT *`만 사용한다. 수신 시각은 필요하면 Lambda 처리 시각 또는 S3 object metadata를 기준으로 별도 계산한다.

S3 raw key와 object body는 아래 기준으로 연결한다.

```text
raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
```

`message_id`는 local outbox 파일명, MQTT payload envelope, S3 raw object key, Lambda/DynamoDB `source_message_id`를 잇는 추적 키다.

## 보류한 선택지

이번 확정에서 제외한 선택지는 아래와 같다.

| 선택지 | 보류 이유 |
| --- | --- |
| `sensor`, `ai_result`, `node_status`, `workload_status`, `device_status`, `pipeline_heartbeat` 별도 topic | source type이 많아지고 IoT Rule/S3/Dashboard 처리가 복잡해짐 |
| AI 상태 변화 즉시 이벤트 전송 | 현재 모델 성능이 충분히 안정적이지 않아 오탐 민감도가 커질 수 있음 |
| Edge에서 `fire_detected`, `fall_detected`, `bend_detected` 최종 판정 | threshold와 정책을 cloud-side Risk 계산 로직에서 조정하기 어렵게 만듦 |
| `pipeline_heartbeat` 별도 파이프라인 | 운영 부담 증가. 20초 `infra_state` 안에 포함해도 1분 내 health check 가능 |

## 구현 시 반영 위치

- `docs/issues/M4_data-plane.md`: M4 데이터 플레인 이슈 기준
- `apps/factory-a-log-adapter/`: `factory-a` raw/log/status -> canonical JSON 변환 구현
- `apps/edge-iot-publisher/`: local spool/outbox -> IoT Core publish 구현
- `apps/dummy-data-generator/`: `factory-b/c` canonical JSON 가데이터 생성 구현
- `configs/runtime/runtime-config.yaml`: Risk field/weight 설정
- `infra/foundation/iot_rule.tf`: IoT Rule S3 raw partition
- Lambda data processor: cloud-side `pipeline_status` 계산, Risk 계산, DynamoDB/S3 processed 저장
