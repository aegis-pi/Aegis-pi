# Dummy Data 생성과 Risk Scenario 운영 기준

상태: 구현 기준 source of truth  
기준일: 2026-06-04
관련 문서:

- `docs/ops/22_factory_bc_testbed_data_plane.md`
- `docs/ops/23_data_pipeline.md`
- `apps/dummy-sensor/docs/factory-b-c-dummy-systemd-runbook.md`
- `docs/specs/iot_data_format.md`

## 목적

이 문서는 `factory-b`, `factory-c` 테스트베드에서 dummy data가 어떻게 생성되고, outbox와 publisher를 거쳐 AWS 데이터 파이프라인으로 들어가며, 이후 Lambda에서 Risk Score가 어떻게 계산되는지 한 흐름으로 정리한다.

또한 그래프를 흔드는 랜덤 node down을 제거하고, 향후 장애 시나리오를 명시적으로 켜고 끄는 운영 방식을 기준으로 둔다.

## 전체 흐름

```text
factory-b/c VM
  -> local dummy generator systemd
      -> /var/lib/aegis/outbox/*.json
      -> Linux cron outbox cleanup

factory-b/c K3s
  -> edge-iot-publisher Pod
      -> hostPath /var/lib/aegis/outbox
      -> AWS IoT Core topic aegis/{factory_id}/{source_type}

AWS
  -> IoT Rule
      -> S3 raw
      -> AEGIS-Lambda-DataProcessor
          -> normalize factory_state / infra_state
          -> calculate risk-v0.2.0
          -> DynamoDB LATEST / HISTORY#STATE
          -> S3 processed

  -> AEGIS-Lambda-GraphAggregator5m
      -> DynamoDB HISTORY#STATE
      -> DynamoDB GRAPH#5M
      -> S3 processed_agg

  -> AEGIS-Schedule-DataProcessorRefresh1m
      -> AEGIS-Lambda-DataProcessor action=refresh_pipeline_status
      -> stale factory의 pipeline_status / risk 재계산
      -> DynamoDB LATEST / HISTORY#STATE
      -> S3 processed state_snapshot
```

## 생성 컴포넌트

`factory-b/c`는 실제 센서 대신 VM 로컬 script가 canonical JSON을 만든다. Kubernetes Deployment로 dummy generator를 띄우지 않는다.

현재 표준 운영에서 dummy generator는 **worker VM의 systemd service**로 실행된다. master VM에서 generator를 실행하면 master-local `/var/lib/aegis/outbox`에만 JSON이 생성되고, worker node에 배포된 K3s `edge-iot-publisher`가 읽는 hostPath와 분리된다. 따라서 S3 raw, S3 processed, DynamoDB LATEST/HISTORY 검증 대상은 worker-local outbox에서 생성된 데이터다.

접근 정보는 보안 정보로 취급한다. 문서에는 SSH user, host/IP, password를 기록하지 않고, 운영자는 `scripts/ops/manage-dummy-generators.sh`가 읽는 로컬 env 파일이나 별도 보안 저장소로 관리한다.

| Factory | Generator | 실행 방식 | 기본 profile |
| --- | --- | --- | --- |
| `factory-b` | `apps/dummy-sensor/factory_b_dummy_generator.py` | `aegis-factory-b-dummy-generator.service` | `stable-lab` |
| `factory-c` | `apps/dummy-sensor/factory_c_dummy_generator.py` | `aegis-factory-c-dummy-generator.service` | `noisy-vm` |

공통 helper:

| 파일 | 역할 |
| --- | --- |
| `apps/dummy-sensor/k8s_state.py` | Kubernetes workload 상태 조회 helper |
| `apps/edge-iot-publisher/edge_iot_publisher.py` | outbox JSON을 IoT Core로 publish |
| `scripts/ops/aegis-outbox-cleanup.sh` | 오래된 outbox JSON 정리 |

## 생성 주기

| source_type | 기본 주기 | 목적 |
| --- | ---: | --- |
| `factory_state` | 3초 | 센서/AI dummy signal 생성, Risk Score 주 입력 |
| `infra_state` | 20초 | node/workload/device/heartbeat 상태 생성 |

generator는 `--loop` 모드에서 두 주기를 독립적으로 관리한다. 각 메시지는 `message_id`를 파일명으로 사용하고, `outbox/tmp`에 먼저 쓴 뒤 최종 `.json`으로 atomic rename한다.

```text
/var/lib/aegis/outbox/tmp/<message_id>.*.tmp
  -> /var/lib/aegis/outbox/<message_id>.json
```

## factory_state 생성 로직

`factory_state`는 센서 평균값과 AI score를 담는다.

공통 payload 구조:

```json
{
  "aggregation_window_seconds": 3,
  "sensor": {
    "sample_count": 1,
    "temperature_celsius_avg": 24.1,
    "humidity_percent_avg": 55.3,
    "pressure_hpa_avg": 1010.66
  },
  "ai_result": {
    "sample_count": 1,
    "fire_score": 0.0,
    "fall_score": 0.0,
    "bend_score": 0.0,
    "abnormal_sound": "none"
  }
}
```

factory별 baseline 기본값:

| 항목 | factory-b | factory-c |
| --- | ---: | ---: |
| temperature baseline | 24.5 | 27.0 |
| temperature jitter | 3.0 | 4.0 |
| humidity baseline | 45.0 | 52.0 |
| humidity jitter | 8.0 | 10.0 |
| pressure baseline | 1013.5 | 1012.0 |
| pressure jitter | 1.5 | 2.0 |
| abnormal_sound | `brief lab impact` | `intermittent vibration` |

기본 profile은 순수 확률 기반 anomaly가 아니라 `랜덤 간격 + round-robin 이벤트 타입 + 랜덤 값` 구조다. baseline jitter는 매번 유지하고, 이벤트가 due일 때만 sensor spike나 AI score를 주입한다. Sensor spike는 기본 30초 동안 유지해 LATEST 기반 화면에서도 관찰할 수 있게 한다.

| 이벤트 | factory-b stable-lab | factory-c noisy-vm |
| --- | --- | --- |
| AI event interval | 25~30분 | 25~30분 |
| AI event type | `ai_warning` | `ai_warning`, `ai_critical` |
| AI score | fire/fall/bend 중 1~2개, 0.5~0.8, 0.1 단위 | warning은 fire/fall/bend 중 1~3개, 0.5~0.8, 0.1 단위. critical은 1~3개, 0.8~1.0, 0.1 단위 |
| sensor event interval | 6~10분 | 4~7분 |
| sensor event type | `temperature_high`, `humidity_high`, `pressure_high`, `pressure_low` | `temperature_critical`, `humidity_critical`, `pressure_high_critical`, `pressure_low_critical` |
| sensor event hold | 30초 | 30초 |
| temperature spike | 39.0~45.0 | 45.0~52.0 |
| humidity spike | 88.0~96.0 | 95.0~99.0 |
| pressure high spike | 1055.0~1075.0 | 1070.0~1090.0 |
| pressure low spike | 940.0~960.0 | 930.0~950.0 |

AI event가 발생하지 않으면 `fire_score`, `fall_score`, `bend_score`는 모두 `0.0`이고 `abnormal_sound`는 `none`이다.

### Sensor event 세부 주기

2026-06-02 worker 재검증 기준으로 `/etc/aegis/factory-b-dummy.env`와 `/etc/aegis/factory-c-dummy.env`에는 event interval override가 없다. 따라서 아래 값은 worker에 배포된 코드 기본값이다.

| Factory | Sensor event | 값 범위 | 발생 순서/주기 | 동일 event 재발 | 지속 |
| --- | --- | --- | --- | --- | --- |
| `factory-b` | `temperature_high` | `39.0~45.0 C` | sensor event가 `6~10분`마다 1개씩 round-robin | `24~40분`마다 | `30초` |
| `factory-b` | `humidity_high` | `88.0~96.0 %` | 동일 | `24~40분`마다 | `30초` |
| `factory-b` | `pressure_high` | `1055.0~1075.0 hPa` | 동일 | `24~40분`마다 | `30초` |
| `factory-b` | `pressure_low` | `940.0~960.0 hPa` | 동일 | `24~40분`마다 | `30초` |
| `factory-c` | `temperature_critical` | `45.0~52.0 C` | sensor event가 `4~7분`마다 1개씩 round-robin | `16~28분`마다 | `30초` |
| `factory-c` | `humidity_critical` | `95.0~99.0 %` | 동일 | `16~28분`마다 | `30초` |
| `factory-c` | `pressure_high_critical` | `1070.0~1090.0 hPa` | 동일 | `16~28분`마다 | `30초` |
| `factory-c` | `pressure_low_critical` | `930.0~950.0 hPa` | 동일 | `16~28분`마다 | `30초` |

factory-b는 sensor event 자체가 `6~10분`마다 하나 발생하고, 4개 event를 순서대로 돌기 때문에 특정 event 하나는 `24~40분`마다 다시 온다. factory-c는 sensor event 자체가 `4~7분`마다 하나 발생하므로 특정 event 하나는 `16~28분`마다 다시 온다.

각 sensor event는 `AEGIS_DUMMY_SENSOR_EVENT_HOLD_SECONDS=30` 기본값 때문에 30초 동안 유지된다. `factory_state` 생성 주기가 3초라서 event 한 번당 보통 약 10개 샘플이 high/critical 값으로 나온다.

### AI event 세부 동작

dummy generator는 화재, 넘어짐, 굽힘, 이상소음을 각각 독립 이벤트로 스케줄링하지 않는다. AI 스케줄러는 `ai_warning` 또는 `ai_critical` 이벤트만 만들고, 이벤트가 due일 때 `factory_state.payload.ai_result`의 여러 필드를 한 번에 갱신한다.

| Factory | AI event | 발생/재발 주기 | score 선택 | abnormal_sound | 지속 |
| --- | --- | --- | --- | --- | --- |
| `factory-b` | `ai_warning` | 25~30분마다 | `fire_score`, `fall_score`, `bend_score` 중 1~2개를 랜덤 선택해 `0.5~0.8` 설정 | `brief lab impact` | factory_state 1건 |
| `factory-c` | `ai_warning` | AI event는 25~30분마다 1개, 동일 event는 50~60분마다 | `fire_score`, `fall_score`, `bend_score` 중 1~3개를 랜덤 선택해 `0.5~0.8` 설정 | `intermittent vibration` | factory_state 1건 |
| `factory-c` | `ai_critical` | AI event는 25~30분마다 1개, 동일 event는 50~60분마다 | `fire_score`, `fall_score`, `bend_score` 중 1~3개를 랜덤 선택해 `0.8~1.0` 설정 | `intermittent vibration` | factory_state 1건 |

AI event에는 sensor spike처럼 hold window가 없다. 따라서 이벤트 한 번은 현재 loop에서 생성되는 `factory_state` 1건에만 반영된다.

예시:

```json
{
  "ai_result": {
    "sample_count": 1,
    "fire_score": 0.6,
    "fall_score": 0.0,
    "bend_score": 0.8,
    "abnormal_sound": "brief lab impact"
  }
}
```

override 환경변수:

| 환경변수 | 의미 |
| --- | --- |
| `AEGIS_DUMMY_AI_EVENT_MIN_SECONDS` / `AEGIS_DUMMY_AI_EVENT_MAX_SECONDS` | AI round-robin event 간격 |
| `AEGIS_DUMMY_SENSOR_EVENT_MIN_SECONDS` / `AEGIS_DUMMY_SENSOR_EVENT_MAX_SECONDS` | sensor spike round-robin event 간격 |
| `AEGIS_DUMMY_SENSOR_EVENT_HOLD_SECONDS` | sensor spike 유지 시간. 기본 `30` |
| `AEGIS_DUMMY_INFRA_EVENT_MIN_SECONDS` / `AEGIS_DUMMY_INFRA_EVENT_MAX_SECONDS` | infra 상태 round-robin event 간격 |
| `AEGIS_DUMMY_PIPELINE_GAP_EVENT_MIN_SECONDS` / `AEGIS_DUMMY_PIPELINE_GAP_EVENT_MAX_SECONDS` | freshness gap round-robin event 간격 |

## infra_state 생성 로직

기본 운영에서는 node down을 랜덤으로 만들지 않는다. `factory-b/c` 모두 node 상태는 fixed-ready 기준이다.

기본 payload 특성:

- `node_summary.total=2`
- `node_summary.ready=2`
- `node_summary.not_ready=0`
- 모든 node의 `ready=true`
- 모든 node의 `network_reachability=ok`
- `devices.bme280/camera/microphone.available=true`
- `workloads.dummy-data-generator`와 `workloads.edge-iot-publisher`는 `Running`, `ready=true`
- `heartbeat.dummy_scenario=normal`

infra event가 due이면 기본 ready 상태에 round-robin 이벤트를 한 번 적용한다.

| 이벤트 | factory-b stable-lab | factory-c noisy-vm |
| --- | --- | --- |
| infra event interval | 5~8분 | 3~6분 |
| node/pod | `pods_partial`, `nodes_partial` | `pods_all_unready`, `nodes_all_not_ready` |
| device/storage/network | `device_unavailable`, `storage_warning` | `device_unavailable`, `storage_critical`, `network_unreachable` |

Sensor 외 event 기본 주기:

| Factory | 분류 | Event | 발생/재발 주기 |
| --- | --- | --- | --- |
| `factory-b` | AI | `ai_warning` | `25~30분`마다 |
| `factory-b` | Infra | `storage_warning`, `device_unavailable`, `pods_partial`, `nodes_partial` | infra event가 `5~8분`마다 1개, 동일 event는 `20~32분`마다 |
| `factory-b` | Pipeline gap | `pipeline_warning_gap` | `12~18분`마다 |
| `factory-c` | AI | `ai_warning`, `ai_critical` | AI event가 `25~30분`마다 1개, 동일 event는 `50~60분`마다 |
| `factory-c` | Infra | `pods_all_unready`, `nodes_all_not_ready`, `network_unreachable`, `device_unavailable`, `storage_critical` | infra event가 `3~6분`마다 1개, 동일 event는 `15~30분`마다 |
| `factory-c` | Pipeline gap | `pipeline_critical_gap`, `pipeline_outage_gap` | pipeline event가 `18~30분`마다 1개, 동일 event는 `36~60분`마다 |

pipeline freshness event는 payload에 `pipeline_status_*`를 직접 넣지 않는다. `--loop`에서 `infra_state` 생성을 일정 시간 건너뛰어 DataProcessor가 `LATEST.last_infra_state_at` 기준으로 계산하게 한다.

| Factory | freshness gap event |
| --- | --- |
| `factory-b` | `pipeline_warning_gap`: 75~105초 |
| `factory-c` | `pipeline_critical_gap`: 135~180초, `pipeline_outage_gap`: 301~330초 |

예시:

```json
{
  "heartbeat": {
    "agent_status": "alive",
    "cluster_state_source": "synthetic",
    "dummy_scenario": "normal",
    "last_spool_write_status": "unknown",
    "last_spool_write_at": null
  },
  "node_summary": {
    "total": 2,
    "ready": 2,
    "not_ready": 0
  }
}
```

`AEGIS_CLUSTER_STATE_MODE=kubernetes`를 쓰더라도 node ready는 그래프 안정성을 위해 fixed-ready synthetic node를 유지한다. 이 모드에서는 workload만 Kubernetes에서 읽고, node down은 scenario에서만 발생시킨다.

## outbox 정리 cron

2026-05-29 기준 factory-b/c에는 Linux cron 기반 cleanup이 추가됐다. Kubernetes CronJob이 아니다.

설치 파일:

```text
/opt/aegis/bin/aegis-outbox-cleanup.sh
/etc/cron.d/aegis-outbox-cleanup
```

cron:

```cron
0 3 */3 * * root AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox AEGIS_OUTBOX_CLEANUP_MIN_AGE_MINUTES=1440 /opt/aegis/bin/aegis-outbox-cleanup.sh
```

정책:

- 3일에 한 번 실행
- `/var/lib/aegis/outbox/*.json`만 삭제 대상
- 최근 24시간 파일은 유지
- `tmp/` 디렉터리는 정리하지 않음
- 로그는 `/var/log/aegis-outbox-cleanup.log`에 남김

이 cleanup은 오래된 backlog가 뒤늦게 publish되어 그래프와 Risk Score 해석을 흐리는 문제를 줄이기 위한 장치다.

## Publisher와 IoT 전송

`edge-iot-publisher`는 K3s Pod로 배포된다. VM 로컬 publisher systemd는 legacy/manual smoke 용도이며 표준 운영에서는 켜지 않는다.

publisher 동작:

1. hostPath `/var/lib/aegis/outbox`를 scan
2. `.json` 파일만 publish 대상으로 선택
3. `published_at`과 `data_plane_instance_id`를 publish 직전 값으로 덮어씀
4. `aegis/{factory_id}/{source_type}` topic으로 publish
5. 성공한 파일 삭제
6. invalid JSON은 quarantine 처리

topic 예:

```text
aegis/factory-b/factory_state
aegis/factory-b/infra_state
aegis/factory-c/factory_state
aegis/factory-c/infra_state
```

## AWS 저장 경로

IoT Rule은 원본을 S3 raw에 저장하고, 동시에 DataProcessor Lambda를 호출한다.

raw:

```text
s3://aegis-bucket-data/raw/{factory_id}/{source_type}/yyyy=YYYY/mm=MM/dd=DD/{message_id}.json
```

processed:

```text
s3://aegis-bucket-data/processed/{factory_id}/factory_state/yyyy=YYYY/mm=MM/dd=DD/hh=HH/{message_id}.json
s3://aegis-bucket-data/processed/{factory_id}/infra_state/yyyy=YYYY/mm=MM/dd=DD/hh=HH/{message_id}.json
s3://aegis-bucket-data/processed/{factory_id}/risk_score/yyyy=YYYY/mm=MM/dd=DD/hh=HH/{message_id}.json
s3://aegis-bucket-data/processed/{factory_id}/state_snapshot/yyyy=YYYY/mm=MM/dd=DD/hh=HH/{updated_at}.json
```

DynamoDB:

```text
Table: AEGIS-DynamoDB-FactoryStatus

pk = FACTORY#{factory_id}
sk = LATEST
sk = HISTORY#STATE#{updated_at}
sk = GRAPH#5M#{bucket_start}
```

## Risk Score 계산 흐름

Risk Score는 `apps/data-processor/processor/risk.py`의 `risk-v0.2.0` 로직이 계산한다.

입력:

- 최신 `factory_state`
- 최신 `infra_state`
- `pipeline_status`

처리 위치:

- `factory_state` 수신 시: 최신 `infra_state`를 DynamoDB `LATEST`에서 가져와 함께 계산
- `infra_state` 수신 시: 최신 `factory_state`가 있으면 risk를 재계산하고 `LATEST`에 반영
- 1분 refresh 시: 새 메시지가 없어도 최신 `LATEST.last_infra_state_at` 기준으로 `pipeline_status`를 재계산하고, 가능한 경우 risk도 재계산

출력 구조:

```json
{
  "score": 100,
  "level": "safe",
  "base_score": 100,
  "base_level": "safe",
  "top_causes": [],
  "gates": [],
  "calculation_version": "risk-v0.2.0",
  "calculated_at": "2026-05-29T06:01:53.176Z"
}
```

`base_score`는 weighted contribution만 반영한 점수이고, `score`는 gate cap까지 적용한 최종 점수다.

## Weighted contribution

각 field는 0-1 severity를 계산하고 weight만큼 감점한다.

| Field | Weight | Source |
| --- | ---: | --- |
| temperature | 10 | factory_state |
| humidity | 5 | factory_state |
| pressure | 5 | factory_state |
| ai_event_rate | 15 | factory_state |
| node_status | 20 | infra_state |
| pod_health | 15 | infra_state |
| device_availability | 10 | infra_state |
| data_freshness | 10 | pipeline_status |
| storage_pressure | 5 | infra_state |
| network_reachability | 5 | infra_state |

AI score는 `fire_score`, `fall_score`, `bend_score`를 각각 별도 weighted field로 계산하지 않는다. 세 score의 최댓값을 `ai_event_rate` severity의 기본값으로 쓰고, `abnormal_sound`가 `none`이나 빈 문자열이 아니면 작은 bonus를 더한다. 따라서 `risk.top_causes`에는 대개 `fire_score`, `fall_score`, `bend_score` 개별 이름이 아니라 `ai_event_rate`가 원인 field로 들어간다.

AI gate 기준:

| 조건 | Gate | Level cap |
| --- | --- | --- |
| `max(fire_score, fall_score, bend_score) >= 0.95` | `ai_score_critical` | danger |
| `max(fire_score, fall_score, bend_score) >= 0.8` | `ai_score_warning` | warning |
| `max(fire_score, fall_score, bend_score) >= 0.6` and `abnormal_sound != none` | `ai_score_warning` | warning |

계산 개념:

```text
base_score = 100 - sum(weight * severity)
base_level = level_from_score(base_score)
```

level 기준:

| Score | Level |
| ---: | --- |
| 85-100 | safe |
| 50-84 | warning |
| 0-49 | danger |

## Gate cap

gate는 특정 조건에서 최종 score 상한을 강제로 낮춘다. 그래서 base_score가 높아도 gate가 걸리면 최종 level이 더 나빠질 수 있다.

| Gate 예시 | Cap | 의미 |
| --- | ---: | --- |
| `nodes_all_not_ready` | 0 | 모든 node가 not ready면 최종 0점 |
| danger gate | 49 | danger로 강등 |
| warning gate | 84 | warning으로 강등 |

예:

```text
base_score = 80
gate = nodes_all_not_ready(score_cap=0)
score = 0
level = danger
```

따라서 dummy generator 기본 운영에서 node가 랜덤으로 내려가면 그래프가 불안정해진다. 이 때문에 node down은 기본 생성 로직에서 제거하고 scenario에서만 명시적으로 발생시키도록 바꿨다.

## Top causes

`top_causes`는 점수에 영향을 준 주요 원인을 보여준다. weighted cause와 gate cause가 함께 들어갈 수 있다.

예상 형태:

```json
{
  "field": "node_status",
  "reason": "nodes_all_not_ready",
  "value": "0/2",
  "contribution": 20.0,
  "severity": 1.0,
  "source": "infra_state"
}
```

gate를 통과한 원인은 `gates`에도 남는다. 운영자는 `score`만 보지 말고 `base_score`, `gates`, `top_causes`를 같이 봐야 한다.

## Scenario 운영 방식

기본 운영:

```text
AEGIS_DUMMY_SCENARIO=normal
AEGIS_CLUSTER_STATE_MODE=synthetic
```

이 상태에서는 node가 항상 ready다.

node down scenario:

```text
AEGIS_DUMMY_SCENARIO=node_down
AEGIS_DUMMY_SCENARIO_DOWN_NODES=worker1
```

factory-c:

```text
AEGIS_DUMMY_SCENARIO=node_down
AEGIS_DUMMY_SCENARIO_DOWN_NODES=factory-c-worker
```

scenario 적용 절차:

1. 대상 factory의 env 파일 수정
2. generator systemd 재시작
3. `--once infra_state --no-write --pretty`로 payload 확인
4. CloudWatch DataProcessor 로그에서 risk score 확인
5. DynamoDB `LATEST.risk.gates`와 `top_causes` 확인
6. 테스트 종료 후 `AEGIS_DUMMY_SCENARIO=normal`로 복구

factory-b 예:

```bash
sudo sed -i 's/^AEGIS_DUMMY_SCENARIO=.*/AEGIS_DUMMY_SCENARIO=node_down/' /etc/aegis/factory-b-dummy.env
sudo sed -i '/^AEGIS_DUMMY_SCENARIO_DOWN_NODES=/d' /etc/aegis/factory-b-dummy.env
echo 'AEGIS_DUMMY_SCENARIO_DOWN_NODES=worker1' | sudo tee -a /etc/aegis/factory-b-dummy.env
sudo systemctl restart aegis-factory-b-dummy-generator.service
```

복구:

```bash
sudo sed -i 's/^AEGIS_DUMMY_SCENARIO=.*/AEGIS_DUMMY_SCENARIO=normal/' /etc/aegis/factory-b-dummy.env
sudo sed -i '/^AEGIS_DUMMY_SCENARIO_DOWN_NODES=/d' /etc/aegis/factory-b-dummy.env
sudo systemctl restart aegis-factory-b-dummy-generator.service
```

factory-c는 service/env 파일명을 `factory-c`로 바꿔서 적용한다.

## 검증 명령

로컬 테스트:

```bash
python3 -m pytest apps/dummy-sensor/tests -q
```

로컬 preview:

```bash
python3 apps/dummy-sensor/factory_b_dummy_generator.py --once infra_state --no-write --pretty

AEGIS_DUMMY_SCENARIO=node_down \
AEGIS_DUMMY_SCENARIO_DOWN_NODES=worker1 \
python3 apps/dummy-sensor/factory_b_dummy_generator.py --once infra_state --no-write --pretty
```

서비스 확인:

```bash
systemctl is-active aegis-factory-b-dummy-generator.service
systemctl is-active aegis-factory-c-dummy-generator.service
```

cron 확인:

```bash
cat /etc/cron.d/aegis-outbox-cleanup
systemctl is-active cron
```

cleanup dry-run 성격의 안전 검증:

```bash
tmpdir="$(mktemp -d /tmp/aegis-cleanup-test.XXXXXX)"
touch -d '2 days ago' "$tmpdir/old.json"
touch "$tmpdir/new.json"
AEGIS_OUTBOX_DIR="$tmpdir" \
AEGIS_OUTBOX_CLEANUP_LOG_FILE="$tmpdir/cleanup.log" \
  /opt/aegis/bin/aegis-outbox-cleanup.sh
find "$tmpdir" -maxdepth 1 -type f -printf '%f\n' | sort
```

기대 결과:

```text
cleanup.log
new.json
```

DataProcessor 로그 확인:

```bash
aws logs tail /aws/lambda/AEGIS-Lambda-DataProcessor --since 10m --format short
```

DynamoDB LATEST 확인:

```bash
aws dynamodb get-item \
  --table-name AEGIS-DynamoDB-FactoryStatus \
  --key '{"pk":{"S":"FACTORY#factory-c"},"sk":{"S":"LATEST"}}' \
  --query 'Item.{updated_at:updated_at.S,last_factory_state_at:last_factory_state_at.S,last_infra_state_at:last_infra_state_at.S,nodes_ready:infra_state.M.nodes_ready.N,nodes_total:infra_state.M.nodes_total.N,risk:risk.M}' \
  --output json
```

## 운영 주의사항

- 접속 비밀번호, private key, certificate 원문은 문서에 남기지 않는다.
- VM 로컬 publisher systemd와 K3s `edge-iot-publisher`를 동시에 켜지 않는다.
- node down은 기본 생성 로직에 넣지 않는다.
- scenario를 켠 뒤에는 반드시 종료 시점과 복구 여부를 기록한다.
- outbox cleanup은 최근 24시간 파일을 남기므로, publisher 장애가 24시간 이상 지속되면 일부 오래된 파일은 삭제될 수 있다.
- 그래프 이상을 볼 때는 `LATEST`만 보지 말고 `HISTORY#STATE`, S3 raw, CloudWatch 로그, outbox backlog를 같이 확인한다.

## 2026-05-29 적용 결과

적용 내용:

- factory-b/c generator 코드 배포
- factory-b/c env에 `AEGIS_DUMMY_SCENARIO=normal` 추가
- 기본 node 상태 fixed-ready 유지
- `node_down` scenario에서만 node/workload not ready 생성
- factory-b/c Linux cron에 outbox cleanup 등록
- local test `apps/dummy-sensor/tests`: 12 passed
- 원격 sample infra_state 확인:
  - `dummy_scenario=normal`
  - `node_summary.ready=2`
  - `node_summary.not_ready=0`

Risk Score 관련 적용 내용:

- `risk-v0.2.0`은 factory_state, infra_state, pipeline_status를 함께 사용한다.
- `nodes_all_not_ready` gate는 최종 score를 0으로 cap한다.
- 현재 dummy 기본 운영에서는 node가 항상 ready이므로 해당 gate는 scenario 없이는 발생하지 않아야 한다.

## 2026-05-29 factory-a stale Risk 점검 결과

현상:

- `factory-a`가 실제로 down/무수신 상태인데 DynamoDB LATEST의 `risk.score=100`이 계속 표시됐다.

원인 분리:

- S3 raw/processed와 DynamoDB LATEST 기준 `factory-a` 마지막 입력은 `2026-05-28T07:54Z`에서 멈춰 있었다.
- 기존 구조는 IoT 메시지가 들어올 때만 `pipeline_status`와 `risk`를 갱신했다.
- 따라서 메시지가 완전히 끊긴 factory는 stale LATEST가 그대로 남았고, Dashboard/API가 LATEST를 그대로 읽으면 100점으로 보일 수 있었다.
- 마지막 raw `infra_state` payload 자체는 `node_summary.ready=3/3`, node `ready=true`였지만, 과거 processed/LATEST에는 구형 normalizer 결과로 `nodes_ready=0/3`이 남아 있었다. 새 `infra_state`가 들어오면 현재 normalizer 기준으로 덮어써진다.

수정:

- DataProcessor Lambda에 `action=refresh_pipeline_status` 경로를 추가했다.
- `AEGIS-Schedule-DataProcessorRefresh1m`가 1분마다 `factory-a,b,c`를 refresh한다.
- refresh는 `LATEST.last_infra_state_at` 기준으로 `pipeline_status`를 현재 시각에 맞게 재계산하고, 기존 `factory_state`/`infra_state`와 함께 risk를 재계산한다.

검증:

```text
Lambda LastUpdateStatus: Successful
Scheduler: AEGIS-Schedule-DataProcessorRefresh1m ENABLED, rate(1 minute)
factory-a LATEST:
  pipeline_status.status = critical
  latest_infra_state_age_seconds > 82000
  risk.score = 0
  risk.level = danger
  gates = nodes_all_not_ready, pipeline_status_critical
factory-b/c LATEST:
  pipeline_status.status = normal
  risk.score = 100
S3:
  processed/factory-a/state_snapshot/yyyy=2026/mm=05/dd=29/hh=06/... 신규 생성 확인
CloudWatch:
  pipeline refresh done 로그가 1분 주기로 반복됨
```
