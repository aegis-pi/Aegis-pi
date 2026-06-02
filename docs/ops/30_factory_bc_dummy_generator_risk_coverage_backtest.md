# Factory B/C Dummy Generator Risk Coverage Backtest

상태: 배포 및 검증 기록  
기준일: 2026-06-02  
관련 문서:

- `docs/ops/27_dummy_data_generation_and_risk_scenarios.md`
- `docs/ops/23_data_pipeline.md`
- `docs/specs/data_storage_pipeline.md`
- `apps/dummy-sensor/README.md`

## 목적

`factory-b`, `factory-c` dummy generator가 Risk Score의 `risk.top_causes`를 더 다양하게 만들 수 있도록 수정하고, VM 배포 후 실제 데이터 생성 및 AWS 저장 파이프라인을 확인한 결과를 기록한다.

이번 작업의 범위는 dummy generator 입력 다양화다. `apps/data-processor/processor/risk.py`의 Risk 계산 로직과 DynamoDB/S3 저장 계약은 변경하지 않았다.

## 변경 요약

수정 파일:

| 파일 | 변경 |
| --- | --- |
| `apps/dummy-sensor/factory_b_dummy_generator.py` | stable-lab profile에 round-robin sensor/infra/AI/freshness 이벤트 추가 |
| `apps/dummy-sensor/factory_c_dummy_generator.py` | noisy-vm profile에 warning/critical/gate 이벤트 추가 |
| `apps/dummy-sensor/tests/test_factory_b_dummy_generator.py` | AI score, sensor spike, infra event, freshness gap, outbox idempotency 테스트 추가 |
| `apps/dummy-sensor/tests/test_factory_c_dummy_generator.py` | AI score, critical sensor spike, noisy infra event, outage gap 테스트 추가 |
| `apps/dummy-sensor/README.md` | 확률 기반 anomaly 설명을 event schedule 기반 profile 설명으로 갱신 |
| `docs/ops/27_dummy_data_generation_and_risk_scenarios.md` | 운영 기준에 새 event schedule과 override 환경변수 반영 |

핵심 설계:

- 순수 확률 기반 anomaly를 제거하고 `랜덤 간격 + round-robin 이벤트 타입 + 랜덤 값` 구조로 변경했다.
- baseline sensor jitter는 유지한다.
- AI event 기본 간격은 25~30분이다.
- AI event 발생 시 `fire_score`, `fall_score`, `bend_score` 중 일부만 활성화한다.
- AI score 값은 `0.5~1.0` 범위의 `0.1` 단위 값이다.
- pipeline freshness 이벤트는 payload에 `pipeline_status_*`를 직접 넣지 않고 `--loop`에서 `infra_state` 생성을 skip해서 만든다.

## Profile

### factory-b stable-lab

기본 성격은 warning 중심이다.

| 영역 | 기본 이벤트 |
| --- | --- |
| AI | `ai_warning`, 25~30분 간격 |
| sensor | `temperature_high`, `humidity_high`, `pressure_high`, `pressure_low`, 6~10분 간격 |
| infra | `storage_warning`, `device_unavailable`, `pods_partial`, `nodes_partial`, 5~8분 간격 |
| freshness | `pipeline_warning_gap`, 45~55초 infra skip |

### factory-c noisy-vm

기본 성격은 warning/critical/gate 확인용이다.

| 영역 | 기본 이벤트 |
| --- | --- |
| AI | `ai_warning`, `ai_critical`, 25~30분 간격 |
| sensor | `temperature_critical`, `humidity_critical`, `pressure_high_critical`, `pressure_low_critical`, 4~7분 간격 |
| infra | `pods_all_unready`, `nodes_all_not_ready`, `network_unreachable`, `device_unavailable`, `storage_critical`, 3~6분 간격 |
| freshness | `pipeline_critical_gap`, `pipeline_outage_gap`, 70~120초 또는 301~330초 infra skip |

## Local Test

실행 명령:

```bash
python3 -m unittest discover -s apps/dummy-sensor/tests
```

결과:

```text
Ran 23 tests in 0.029s
OK
```

검증한 항목:

- AI score가 `0.5~1.0` 범위이고 `0.1` 단위인지 확인
- 기본 상태에서 매번 AI event가 발생하지 않는지 확인
- sensor spike가 Risk threshold를 넘는 값을 만들 수 있는지 확인
- infra event가 node/pod/device/storage/network 상태를 만들 수 있는지 확인
- node down은 explicit scenario 또는 event에서만 발생하는지 확인
- `write_outbox()` idempotency 유지 확인

## VM Deployment

대상:

| Factory | Host | Service |
| --- | --- | --- |
| `factory-b` | `100.98.121.77` | `aegis-factory-b-dummy-generator.service` |
| `factory-c` | `100.76.243.72` | `aegis-factory-c-dummy-generator.service` |

적용 방식:

1. 수정된 generator 파일을 VM의 `/tmp`로 복사했다.
2. 기존 `/opt/aegis/dummy-sensor/factory_*_dummy_generator.py`는 timestamp suffix로 백업했다.
3. 새 파일을 `/opt/aegis/dummy-sensor/`에 `root:root`, `0755`로 설치했다.
4. systemd service를 재시작했다.

최종 상태:

```text
factory-b generator service: active
factory-c generator service: active
```

## VM No-Write Preview

운영 outbox를 건드리지 않고 override 환경변수로 event interval을 `0`으로 낮춰 새 generator가 이벤트 payload를 만들 수 있는지 확인했다.

### factory-b preview

확인된 payload 특성:

```text
ai_result.fire_score = 0.6
ai_result.fall_score = 0.0
ai_result.bend_score = 0.0
sensor.temperature_celsius_avg = 34.14
node disk_usage_percent max = 82.83
```

의미:

- AI score가 0.1 단위로 생성됐다.
- temperature high spike가 warning threshold인 32도를 넘었다.
- storage warning threshold인 75%를 넘는 infra payload가 생성됐다.

### factory-c preview

확인된 payload 특성:

```text
ai_result.fire_score = 0.5
ai_result.fall_score = 0.8
ai_result.bend_score = 0.5
sensor.temperature_celsius_avg = 42.02
workload_summary.running = 0
workload_summary.not_running = 2
workloads[].status = CrashLoopBackOff
```

의미:

- AI score가 0.1 단위로 여러 field에 분산 생성됐다.
- temperature critical threshold인 38도를 넘었다.
- `pods_all_unready` 계열 Risk gate를 만들 수 있는 infra payload가 생성됐다.

## Runtime Data Generation

배포 후 systemd 로그에서 양쪽 VM 모두 기본 주기로 outbox JSON을 생성하는 것을 확인했다.

| Factory | factory_state | infra_state |
| --- | --- | --- |
| `factory-b` | 약 3초 주기 | 약 20초 주기 |
| `factory-c` | 약 3초 주기 | 약 20초 주기 |

최신 sample payload는 정상 baseline 상태였다.

예시:

```text
factory-b latest factory_state:
  source_timestamp = 2026-06-02T01:51:15Z
  ai_result = all 0.0
  temperature = 26.07
  humidity = 44.59
  pressure = 1012.74

factory-c latest factory_state:
  source_timestamp = 2026-06-02T01:51:20Z
  ai_result = all 0.0
  temperature = 29.85
  humidity = 53.32
  pressure = 1010.64
```

이는 기본 AI event interval이 25~30분이므로 정상적인 결과다.

## Publisher Check

K3s `edge-iot-publisher` Pod 상태:

| Factory | Pod 상태 |
| --- | --- |
| `factory-b` | `Running` |
| `factory-c` | `Running` |

publisher 로그에서 아래 topic으로 publish되는 것을 확인했다.

```text
aegis/factory-b/factory_state
aegis/factory-b/infra_state
aegis/factory-c/factory_state
aegis/factory-c/infra_state
```

관찰된 주의점:

- 양쪽 모두 간헐적으로 `MQTT CONNACK rejected`가 발생했다.
- 동일 파일은 이후 재시도되어 publish 성공 로그가 찍혔다.
- 따라서 일시적 MQTT 연결 거부가 있으나 publish path는 살아 있다.

## DynamoDB Check

테이블:

```text
AEGIS-DynamoDB-FactoryStatus
```

확인한 item:

```text
pk = FACTORY#factory-b, sk = LATEST
pk = FACTORY#factory-c, sk = LATEST
```

배포 후 LATEST 갱신 확인:

```text
factory-b:
  last_factory_state_at = 2026-06-02T01:56:10Z
  last_infra_state_at = 2026-06-02T01:56:03Z
  pipeline_status.status = normal
  risk.score = 100
  risk.level = safe

factory-c:
  last_factory_state_at = 2026-06-02T01:56:12Z
  last_infra_state_at = 2026-06-02T01:56:03Z
  pipeline_status.status = normal
  risk.score = 100
  risk.level = safe
```

`HISTORY#STATE`도 최신 timestamp로 계속 생성되는 것을 확인했다.

예시:

```text
factory-b HISTORY#STATE#2026-06-02T01:53:45.204Z
factory-c HISTORY#STATE#2026-06-02T01:53:48.005Z
```

## S3 Check

bucket:

```text
aegis-bucket-data
```

확인한 prefix:

```text
raw/factory-b/factory_state/yyyy=2026/mm=06/dd=02/
raw/factory-b/infra_state/yyyy=2026/mm=06/dd=02/
raw/factory-c/factory_state/yyyy=2026/mm=06/dd=02/
raw/factory-c/infra_state/yyyy=2026/mm=06/dd=02/
processed/factory-b/risk_score/yyyy=2026/mm=06/dd=02/hh=01/
processed/factory-c/risk_score/yyyy=2026/mm=06/dd=02/hh=01/
processed/factory-b/state_snapshot/yyyy=2026/mm=06/dd=02/hh=01/
processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=01/
```

확인 결과:

- `raw/`에 factory_state/infra_state 원본 JSON이 최신 timestamp로 저장됐다.
- `processed/*/risk_score/`에 Risk 결과 JSON이 저장됐다.
- `processed/*/state_snapshot/`에 state snapshot JSON이 저장됐다.

예시:

```text
raw/factory-b/factory_state/.../factory-b:factory_state:worker1:2026-06-02T01:52:34Z.json
raw/factory-c/factory_state/.../factory-c:factory_state:factory-c-worker:2026-06-02T01:52:33Z.json
processed/factory-b/risk_score/.../factory-b:factory_state:worker1:2026-06-02T01:52:34Z.json
processed/factory-c/risk_score/.../factory-c:factory_state:factory-c-worker:2026-06-02T01:52:39Z.json
```

## Risk Top Causes Observation

배포 직후 `LATEST.risk.top_causes`는 정상 baseline factory_state에 의해 빠르게 덮여 빈 배열인 경우가 많았다.

`HISTORY#STATE`에는 `top_causes`가 있는 항목이 존재했다. 다만 배포 직후 조회된 값에는 아래처럼 기존 generator/backlog에서 생성된 AI score가 섞여 있었다.

```text
factory-b:
  reason = ai_score_warning
  field = ai_event_rate
  value = 0.6803 또는 0.6653

factory-c:
  reason = ai_score_critical
  field = ai_event_rate
  value = 0.9663
```

이 값들은 새 generator의 0.1 단위 score가 아니라 기존 backlog payload의 소수점 score 형태다. 따라서 AWS 저장 경로는 정상이나, 배포 직후 `risk.top_causes` 다양성 검증은 outbox backlog 영향과 섞인다.

## Outbox Backlog

배포 후 outbox file count:

```text
factory-b: 약 64,816 files
factory-c: 약 64,745 files
```

추가 관찰:

- 1시간 이상 된 JSON 파일이 양쪽 모두 6만 개 이상 남아 있었다.
- 2026-05-31 timestamp의 오래된 JSON도 outbox에 남아 있었다.
- publisher는 최신 파일을 publish하고 있지만, 선택한 최신 파일이 수십 초 후에도 남아 있는 사례가 있었다.
- `edge_iot_publisher.py` 구현은 publish 성공 후 `path.unlink()`를 수행하므로, backlog가 유지되는 원인은 별도 운영 점검이 필요하다.

가능한 영향:

- 오래된 payload가 뒤늦게 publish되면 DynamoDB HISTORY와 S3 processed에 기존 generator의 risk pattern이 계속 섞인다.
- `risk.top_causes` 다양성 검증 시 새 generator 효과와 기존 backlog 효과가 혼재한다.
- LATEST는 최신 정상 factory_state에 의해 빠르게 덮이므로 event 확인은 HISTORY/S3 processed 기준으로 봐야 한다.

## 결론

확인된 것:

- 새 generator 코드는 VM에 배포됐다.
- systemd service는 양쪽 모두 정상 실행 중이다.
- VM local JSON 생성은 정상이다.
- no-write preview 기준 새 profile이 sensor/infra/AI risk input을 만들 수 있다.
- edge-iot-publisher, IoT Core, DataProcessor, DynamoDB, S3 저장 경로는 동작 중이다.

남은 운영 이슈:

- outbox backlog 정리가 필요하다.
- backlog 정리 전에는 AWS의 `risk.top_causes`에 기존 generator payload가 섞여 보일 수 있다.
- 새 profile의 `temperature`, `humidity`, `pressure`, `pod_health`, `node_status`, `device_availability`, `storage_pressure`, `network_reachability`, `data_freshness` 다양성을 깨끗하게 확인하려면 backlog를 정리하거나 별도 격리 outbox로 재검증해야 한다.

## 권장 다음 단계

1. 운영 승인 후 `/var/lib/aegis/outbox`의 오래된 backlog를 정리한다.
2. 정리 직후 30~60분 동안 DynamoDB `HISTORY#STATE`와 S3 `processed/risk_score`를 관찰한다.
3. factory-b에서는 warning 계열 top_causes가 순환하는지 확인한다.
4. factory-c에서는 critical/gate 계열 top_causes가 순환하는지 확인한다.
5. freshness 확인은 기본 간격상 시간이 걸리므로 `pipeline_warning_gap`, `pipeline_critical_gap`, `pipeline_outage_gap` 발생 시간대를 HISTORY 기준으로 확인한다.
