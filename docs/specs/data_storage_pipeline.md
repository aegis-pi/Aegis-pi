# Data Storage Pipeline and Formats

상태: source of truth
기준일: 2026-06-04

## 목적

이 문서는 AWS IoT Core 수신 이후 데이터를 어디에 어떤 형태로 저장하는지 정의한다.

범위는 아래 저장 계층이다.

```text
DynamoDB LATEST
DynamoDB HISTORY#STATE
DynamoDB GRAPH#5M
DynamoDB CLOUD#infra LATEST/HISTORY
DynamoDB ALERT# alert cooldown/dedupe and confirmation state
S3 raw
S3 processed
S3 processed_agg
```

전송 데이터 포맷 자체는 `docs/specs/iot_data_format.md`를 따른다. 이 문서는 해당 메시지를 cloud-side에서 어떻게 저장하고 Dashboard가 어떻게 조회하는지를 정의한다.

MVP 기준 Dashboard의 현재 상태 조회는 S3 `latest/` 객체가 아니라 DynamoDB LATEST item을 기준으로 한다. S3는 raw 원본 보존과 processed 장기 이력 저장소로 사용한다.
Bedrock 기반 일일 운영 보고서의 MVP 입력도 S3 `processed/`를 기준으로 하며, S3 `raw/` 원본 전체를 Bedrock에 직접 전달하지 않는다.

2026-06-02 기준 Dashboard page와 Dashboard VPC 구현은 별도 담당 범위로 분리한다. 이 repo의 현재 책임은 Dashboard가 읽을 DynamoDB/S3 processed/processed_agg 계약, Risk output 구조, Cloud infra read model, RiskAlertDispatcher alert state, Daily Factory Report 산출물 계약을 최신 상태로 유지하는 것이다.

## 전체 데이터 흐름

최종 MVP 데이터 처리 흐름은 아래 구조를 기준으로 한다.

```text
factory-a-log-adapter / dummy-data-generator
  -> local spool/outbox
  -> edge-iot-publisher
  -> AWS IoT Core
      -> IoT Rule
          -> S3 raw
          -> Lambda
              -> DynamoDB LATEST
              -> DynamoDB HISTORY#STATE
              -> S3 processed
          -> DataProcessorRefresh1m
              -> DynamoDB LATEST freshness/risk refresh
              -> DynamoDB HISTORY#STATE
              -> S3 processed state_snapshot
          -> GraphAggregator5m
              -> DynamoDB GRAPH#5M
              -> S3 processed_agg
          -> CloudInfraFastCollector1m
              -> DynamoDB CLOUD#infra LATEST.fast / HISTORY#FAST
              -> S3 processed/cloud_infra/fast
          -> CloudInfraSlowCollector5m
              -> DynamoDB CLOUD#infra LATEST.slow / HISTORY#SLOW
              -> S3 processed/cloud_infra/slow
          -> S3 processed ObjectCreated
              -> RiskAlertDispatcher
              -> DynamoDB ALERT#{scope} observation confirmation + cooldown/dedupe
              -> Slack webhook routing

Dashboard API/Web
  -> DynamoDB FACTORY#*/LATEST/GRAPH#5M/HISTORY#STATE
  -> DynamoDB CLOUD#infra/LATEST
  -> S3 processed/processed_agg for detail and audit
```

역할:

| 구성 요소 | 역할 |
| --- | --- |
| IoT Core | factory별 MQTT 데이터 수신 진입점 |
| IoT Rule | 수신 원본을 S3 raw에 저장 |
| Lambda data processor | 메시지 정규화, Risk 계산, latest/history/processed 저장 |
| Lambda DataProcessorRefresh1m | 새 메시지가 없는 factory의 pipeline freshness와 risk를 1분마다 재계산 |
| Lambda GraphAggregator5m | HISTORY#STATE를 5분 단위 graph read model로 집계 |
| Lambda CloudInfraFastCollector1m | Backend/ECS/ALB/Lambda/DynamoDB/Scheduler/factory freshness 요약을 수집 |
| Lambda CloudInfraSlowCollector5m | EKS/Kubernetes/ArgoCD/S3 freshness 요약을 수집 |
| Lambda RiskAlertDispatcher | S3 processed snapshot warning/danger 조건 평가, 필요한 warning 연속 관측 확인, cooldown/dedupe 후 Slack 알림 |
| DynamoDB LATEST | Dashboard 카드와 현재 상태 조회용 read model |
| DynamoDB CLOUD#infra LATEST | Cloud infra dashboard 현재 상태 read model |
| DynamoDB GRAPH#5M | 최근 1시간/2시간/24시간 그래프 조회용 5분 집계 |
| DynamoDB HISTORY#STATE | 상세 이력과 GraphAggregator5m 입력 snapshot |
| DynamoDB ALERT# | Slack alert 연속 관측 확인 및 cooldown/dedupe state |
| S3 raw | Edge data-plane 원본 JSON 장기 보존 |
| S3 processed | Lambda 계산 결과와 상태 요약 이력 보존 |
| S3 processed_agg | 5분 graph aggregate 장기 보조 산출물 |

## 저장 계층 구분

| 계층 | 저장 내용 | 조회 목적 | 보존 방식 |
| --- | --- | --- | --- |
| `S3 raw` | Edge data-plane 원본 `factory_state`, `infra_state` | 감사, 재처리, 원본 확인 | 장기 보존 |
| `S3 processed` | Lambda가 계산한 Risk 결과, pipeline summary, status summary | 리포트, 장기 이력, 재처리 비교 | 장기 보존 |
| `S3 processed_agg` | 5분 graph aggregate | 장기 그래프 보조 조회, 감사 | 장기 보존 |
| `DynamoDB LATEST` | 공장별 현재 상태 1건 | 대시보드 상단 카드, 현재 노드 상태 | 계속 overwrite |
| `DynamoDB CLOUD#infra LATEST` | Cloud infra 현재 상태 1건 | Cloud infra dashboard 현재 상태 | 계속 overwrite |
| `DynamoDB HISTORY#STATE` | 전체 상태 snapshot short-term 시계열 | 상세 이력, graph aggregate 입력 | TTL로 최근 N시간/일만 보존 |
| `DynamoDB CLOUD#infra HISTORY` | Cloud infra fast/slow snapshot | 운영 디버깅, 최근 추이 | TTL로 최근 N시간만 보존 |
| `DynamoDB GRAPH#5M` | 5분 단위 sensor/risk/AI/infra 집계 | 최근 그래프 | TTL로 최근 N시간/일만 보존 |
| `DynamoDB ALERT#` | RiskAlertDispatcher observation/cooldown/dedupe item | 일시 warning 및 Slack 중복 알림 억제 | TTL로 최근 alert state만 보존 |

DynamoDB는 원본의 source of truth가 아니다. 원본 정본은 `S3 raw`이고, 처리 결과 이력 정본은 `S3 processed`다. DynamoDB는 Dashboard가 빠르게 읽기 위한 hot store다.

## S3 Raw Path

IoT Rule은 IoT Core 수신 메시지를 원본 그대로 저장한다.

경로:

```text
raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
```

예시:

```text
raw/factory-a/factory_state/yyyy=2026/mm=05/dd=14/factory-a:factory_state:worker2:2026-05-14T12:00:06Z.json
raw/factory-a/infra_state/yyyy=2026/mm=05/dd=14/factory-a:infra_state:cluster:2026-05-14T12:00:20Z.json
```

저장 내용:

- `factory_state`: 온도, 습도, 기압, AI score, 이상소음 대표 라벨
- `infra_state`: heartbeat, node, workload, device 상태 원본 요약

Object body 기준:

- S3 raw object body는 Edge data-plane이 publish한 canonical JSON과 동일한 payload를 저장한다.
- 검증 기준은 `schema_version`, `message_id`, `factory_id`, `node_id`, `source_type`, `source_timestamp`, `published_at`, `data_plane_instance_id`, `payload`다.
- IoT Rule SQL은 `SELECT *`만 사용하고 raw body에 `received_at` 같은 보조 필드를 추가하지 않는다.
- `message_id`는 local outbox 파일명, MQTT payload, S3 raw object key, Lambda 처리 결과의 `source_message_id`를 연결하는 idempotency key다.

## S3 Processed Path

Lambda는 계산 결과와 상태 요약을 S3 processed에 저장한다.

Risk 결과:

```text
processed/{factory_id}/risk_score/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
```

환경 상태 처리 결과:

```text
processed/{factory_id}/factory_state/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
```

인프라 상태 처리 결과:

```text
processed/{factory_id}/infra_state/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
```

전체 상태 snapshot:

```text
processed/{factory_id}/state_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{updated_at}.json
```

Cloud infra fast snapshot:

```text
processed/cloud_infra/fast/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{updated_at}.json
```

Cloud infra slow snapshot:

```text
processed/cloud_infra/slow/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{updated_at}.json
```

5분 그래프 집계:

```text
processed_agg/{factory_id}/metrics_5m/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/mm={MM}.json
```

예시:

```text
processed/factory-a/risk_score/yyyy=2026/mm=05/dd=14/hh=12/factory-a:factory_state:worker2:2026-05-14T12:00:06Z.json
processed/factory-a/infra_state/yyyy=2026/mm=05/dd=14/hh=12/factory-a:infra_state:cluster:2026-05-14T12:00:20Z.json
processed/factory-a/state_snapshot/yyyy=2026/mm=05/dd=14/hh=12/2026-05-14T12:00:06.123Z.json
processed/cloud_infra/fast/yyyy=2026/mm=06/dd=01/hh=15/2026-06-01T15-30-00Z.json
processed/cloud_infra/slow/yyyy=2026/mm=06/dd=01/hh=15/2026-06-01T15-30-00Z.json
processed_agg/factory-a/metrics_5m/yyyy=2026/mm=05/dd=14/hh=12/mm=05.json
```

`S3 processed`는 장기 이력과 재처리 비교를 위한 저장소다. Dashboard의 기본 현재 상태와 최근 그래프는 DynamoDB를 먼저 조회한다.

Processed object body 기준:

- Lambda data processor가 정규화한 입력, Risk 계산 결과, pipeline summary, dashboard summary를 저장한다.
- `source_message_id`에는 원본 canonical JSON의 `message_id`를 저장한다.
- `processed/{factory_id}/risk_score/`는 `factory_state` 처리 결과와 Risk 계산 결과를 담는다.
- `processed/{factory_id}/factory_state/`는 Dashboard 환경 상태 조회에 필요한 정규화 결과를 담는다.
- `processed/{factory_id}/infra_state/`는 인프라 상태와 pipeline status 계산 결과를 담는다.
- `processed/{factory_id}/state_snapshot/`은 DynamoDB `HISTORY#STATE`와 같은 전체 상태 snapshot을 담되, DynamoDB TTL 정책 필드인 `ttl`은 저장하지 않는다.
- `processed/cloud_infra/fast/`와 `processed/cloud_infra/slow/`는 DynamoDB `CLOUD#infra` history snapshot과 같은 구조를 저장하되, DynamoDB TTL 정책 필드인 `ttl`은 저장하지 않는다.
- `processed_agg/{factory_id}/metrics_5m/`은 GraphAggregator5m이 만든 5분 그래프 집계 결과를 담으며, DynamoDB TTL 정책 필드인 `ttl`은 저장하지 않는다.
- `processed/{factory_id}/state_snapshot/`과 `processed/cloud_infra/{fast,slow}/` JSON object는 RiskAlertDispatcher S3 ObjectCreated trigger 입력이다.
- S3 processed는 장기 이력과 재처리 비교용이며, Dashboard current state의 1차 조회 대상은 아니다.

Risk 계산 현재 상태:

- `apps/data-processor/processor/risk.py`에는 `risk-v0.2.0` Risk Score 계산이 구현되어 있으며, factory_state, infra_state, pipeline_status를 함께 사용한다.
- 점수는 높을수록 안전하다. `safe=85~100`, `warning=50~84`, `danger=0~49`다.
- 출력은 `risk.score`, `risk.base_score`, `risk.level`, `risk.base_level`, `risk.top_causes`, `risk.gates`, `risk.calculation_version`, `risk.calculated_at`을 포함한다.
- `nodes_all_not_ready` gate는 최종 `risk.score=0`으로 cap한다. `pipeline_status=critical`은 danger gate로 반영한다.
- `configs/runtime/runtime-config.yaml`에는 weight/threshold/factory override 초안이 있으나, 2026-05-29 기준 Lambda Risk 계산은 아직 이 파일을 읽지 않는다.
- 다음 계약 고도화는 runtime config를 Lambda package 또는 배포 입력으로 연결하고, Risk Twin/Dashboard가 읽을 필드의 안정성을 테스트로 고정하는 것이다.

## DynamoDB Table

테이블명:

```text
AEGIS-DynamoDB-FactoryStatus
```

레이어: `infra/foundation` (영구 리소스. data-pipeline destroy와 무관하게 유지됨)

기본 키:

| 필드 | 의미 |
| --- | --- |
| `pk` | `FACTORY#{factory_id}`, `CLOUD#infra`, `ALERT#{scope}` |
| `sk` | item type과 timestamp |

공통 필드:

| 필드 | 의미 |
| --- | --- |
| `factory_id` | 공장 ID |
| `schema_version` | 저장 스키마 버전 |
| `updated_at` | item 갱신 시각 |
| `source_message_id` | 원본 IoT 메시지 ID |
| `ttl` | HISTORY item 자동 삭제 시각. LATEST에는 사용하지 않음 |

## DynamoDB LATEST

`LATEST` item은 공장별 현재 상태 1건이다.

키:

```text
pk = FACTORY#{factory_id}
sk = LATEST
```

저장 방식:

- `factory_state` 수신 시 `LATEST.factory_state`, `LATEST.risk`, `LATEST.pipeline_status` 갱신
- `infra_state` 수신 시 `LATEST.infra_state`, `LATEST.pipeline_status`, 가능한 경우 `LATEST.risk` 갱신
- DataProcessor 1분 refresh 시 새 메시지가 없어도 `LATEST.pipeline_status`, 가능한 경우 `LATEST.risk` 갱신
- 같은 `pk/sk` item을 계속 overwrite/update 한다
- 과거 이력은 `LATEST`에 남기지 않는다
- `LATEST.source_message_id`는 마지막으로 처리한 메시지 ID를 저장한다
- 중복 `message_id`가 들어오면 같은 처리 결과로 간주하고 item을 중복 증가시키지 않는다

Dashboard 사용처:

- 공장별 현재 Risk 카드
- 현재 환경 상태 요약
- 현재 노드/워크로드/장치 상태
- 현재 pipeline status
- 공장 목록 위험도 정렬

예시:

```json
{
  "pk": "FACTORY#factory-a",
  "sk": "LATEST",
  "factory_id": "factory-a",
  "schema_version": "0.1.0",
  "updated_at": "2026-05-14T12:00:20Z",
  "last_factory_state_at": "2026-05-14T12:00:06Z",
  "last_infra_state_at": "2026-05-14T12:00:20Z",
  "risk": {
    "score": 27.6,
    "level": "danger",
    "top_causes": [
      {
        "field": "temperature",
        "value": 38.2,
        "contribution": 42.86
      },
      {
        "field": "ai_event_rate",
        "value": 0.67,
        "contribution": 19.14
      }
    ],
    "calculated_at": "2026-05-14T12:00:06Z",
    "calculation_version": "risk-v0.2.0"
  },
  "factory_state": {
    "source_message_id": "factory-a:factory_state:worker2:2026-05-14T12:00:06Z",
    "aggregation_window_seconds": 3,
    "sensor": {
      "sample_count": 5,
      "temperature_celsius_avg": 38.2,
      "humidity_percent_avg": 64.0,
      "pressure_hpa_avg": 1011.8
    },
    "ai_result": {
      "sample_count": 3,
      "fire_score": 0.0,
      "fall_score": 0.67,
      "bend_score": 0.2,
      "abnormal_sound": "none"
    }
  },
  "infra_state": {
    "source_message_id": "factory-a:infra_state:cluster:2026-05-14T12:00:20Z",
    "node_summary": {
      "total": 3,
      "ready": 3,
      "not_ready": 0
    },
    "nodes": [
      {
        "node_id": "master",
        "ready": true,
        "cpu_usage_percent": 31.2,
        "memory_usage_percent": 55.4,
        "disk_usage_percent": 42.1
      },
      {
        "node_id": "worker1",
        "ready": true,
        "cpu_usage_percent": 22.8,
        "memory_usage_percent": 48.0,
        "disk_usage_percent": 39.5
      },
      {
        "node_id": "worker2",
        "ready": true,
        "cpu_usage_percent": 44.8,
        "memory_usage_percent": 63.0,
        "disk_usage_percent": 45.5
      }
    ],
    "workload_summary": {
      "total": 3,
      "running": 3,
      "unhealthy": 0,
      "restart_count_total": 0
    },
    "device_summary": {
      "bme280_available": true,
      "camera_available": true,
      "microphone_available": true
    }
  },
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 6,
    "latest_s3_raw_age_seconds": 4
  },
  "dashboard": {
    "display_status": "위험",
    "summary": "넘어짐 score와 온도 상승으로 위험 상태",
    "updated_at": "2026-05-14T12:00:20Z"
  }
}
```

## DynamoDB HISTORY#STATE

`HISTORY#STATE` item은 상세 이력과 graph aggregate 입력을 위한 short-term 시계열이다. `LATEST`와 필드 구조를 동일하게 유지하고, `sk`와 `ttl`만 history용으로 바꾼 스냅샷을 저장한다.

보존:

```text
TTL: HISTORY_TTL_HOURS 값
```

MVP Dashboard는 최근 1시간 또는 2시간 그래프는 `GRAPH#5M`을 기본으로 조회하고, 상세 drill-down은 `HISTORY#STATE`를 조회한다. TTL은 Lambda 환경변수 `HISTORY_TTL_HOURS`로 조정 가능하며, Terraform `dynamodb_history_ttl_hours`가 주입한다.

키:

```text
pk = FACTORY#{factory_id}
sk = HISTORY#STATE#{updated_at}   ← 예: HISTORY#STATE#2026-05-14T12:00:06.123Z
```

저장 방식:

- `factory_state` 수신 시 `LATEST.factory_state`, `LATEST.risk`, `LATEST.pipeline_status`를 부분 갱신한 뒤, 갱신된 `LATEST` 전체를 `HISTORY#STATE#{updated_at}`으로 복사한다.
- `infra_state` 수신 시 `LATEST.infra_state`, `LATEST.pipeline_status`, 가능한 경우 `LATEST.risk`를 부분 갱신한 뒤, 갱신된 `LATEST` 전체를 `HISTORY#STATE#{updated_at}`으로 복사한다.
- DataProcessor 1분 refresh 시 `LATEST.pipeline_status`, 가능한 경우 `LATEST.risk`를 부분 갱신한 뒤, 갱신된 `LATEST` 전체를 `HISTORY#STATE#{updated_at}`으로 복사한다.
- `HISTORY#STATE` item은 `LATEST`와 같은 구조이며, `ttl` 필드만 추가된다.
- 정밀 이력 원본은 S3 raw와 S3 processed에 별도 보존한다.

예시:

```json
{
  "pk": "FACTORY#factory-a",
  "sk": "HISTORY#STATE#2026-05-14T12:00:06.123Z",
  "factory_id": "factory-a",
  "schema_version": "0.1.0",
  "factory_state": {
    "message_id": "factory-a:factory_state:worker2:2026-05-14T12:00:06Z",
    "source_timestamp": "2026-05-14T12:00:06Z",
    "aggregation_window_seconds": 3,
    "temperature_celsius": 38.2,
    "humidity_percent": 64.0,
    "pressure_hpa": 1011.8,
    "sample_count": 5,
    "fire_score": 0.0,
    "fall_score": 0.67,
    "bend_score": 0.2,
    "abnormal_sound": "none",
    "ai_sample_count": 3
  },
  "infra_state": {
    "message_id": "factory-a:infra_state:cluster:2026-05-14T12:00:00Z",
    "source_timestamp": "2026-05-14T12:00:00Z",
    "agent_status": "running",
    "cluster_name": "factory-a",
    "nodes_total": 3,
    "nodes_ready": 3,
    "pods_ready": 12,
    "pods_total": 12,
    "nodes": [],
    "workloads": [],
    "devices": {}
  },
  "risk": {
    "score": 72.4,
    "level": "warning",
    "calculation_version": "risk-v0.2.0"
  },
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 6,
    "latest_s3_raw_age_seconds": 4
  },
  "last_factory_state_at": "2026-05-14T12:00:06Z",
  "last_infra_state_at": "2026-05-14T12:00:00Z",
  "updated_at": "2026-05-14T12:00:06.123Z",
  "ttl": 1760000000
}
```

## DynamoDB GRAPH#5M

`GRAPH#5M` item은 `HISTORY#STATE` snapshot을 5분 단위로 집계한 Dashboard 그래프용 read model이다.

키:

```text
pk = FACTORY#{factory_id}
sk = GRAPH#5M#{bucket_start}   ← 예: GRAPH#5M#2026-05-14T12:05:00Z
```

저장 방식:

- EventBridge Scheduler가 GraphAggregator5m Lambda를 5분 주기로 호출한다.
- GraphAggregator5m은 공장별 `HISTORY#STATE` window를 query한다.
- sensor, risk, AI detection, infra metric을 5분 bucket으로 집계한다.
- DynamoDB에는 `ttl`을 포함해 저장하고, S3 `processed_agg/`에는 `ttl`을 제외해 저장한다.

주요 필드:

| 필드 | 의미 |
| --- | --- |
| `sensor` | temperature/humidity/pressure min/max/mean/first/last |
| `risk` | risk score min/max/mean/first/last |
| `ai_detection` | fire/fall/bend score와 threshold 초과 횟수 |
| `infra.cpu_usage_percent`, `infra.memory_usage_percent`, `infra.disk_usage_percent` | bucket 안 snapshot별 전체 node 평균을 다시 5분 집계한 하위 호환 필드 |
| `infra.nodes[]` | `node_id`별 CPU/memory/disk min/max/mean/first/last 5분 집계 |
| `quality` | source count, expected count, collection rate |

## DynamoDB CLOUD#infra

Cloud infra collector는 같은 DynamoDB 테이블에 별도 read model을 저장한다.

현재 상태:

```text
pk = CLOUD#infra
sk = LATEST
```

최근 이력:

```text
pk = CLOUD#infra
sk = HISTORY#FAST#{updated_at}
ttl = now + 6h

pk = CLOUD#infra
sk = HISTORY#SLOW#{updated_at}
ttl = now + 24h
```

저장 방식:

- `CloudInfraFastCollector1m`은 `LATEST.fast`, `fast_updated_at`, `overall_status`, `updated_at`을 갱신한다.
- `CloudInfraSlowCollector5m`은 `LATEST.slow`, `slow_updated_at`, `overall_status`, `updated_at`을 갱신한다.
- 두 collector는 기존 반대쪽 필드를 보존해서 1분 fast 갱신이 5분 slow 값을 지우지 않고, slow 갱신도 fast 값을 지우지 않는다.
- 각 실행은 TTL이 있는 history item을 추가하고, S3 `processed/cloud_infra/{fast,slow}/...` snapshot을 저장한다.
- `overall_status`는 Cloud 자체 section인 `backend_runtime`, `data_pipeline`, `eks_management`, `storage_freshness`만 사용한다. `fast.factory_freshness`는 대시보드 참고 데이터로 유지하지만 overall 판정에서는 제외한다.

주요 필드:

| 필드 | 의미 |
| --- | --- |
| `overall_status` | Cloud 자체 fast/slow section 중 가장 나쁜 상태. `factory_freshness` 제외 |
| `fast.backend_runtime` | ECS backend service와 ALB target/latency/5xx |
| `fast.backend_runtime.ecs.load_balancers[].targetGroupArn` | ECS service가 현재 참조하는 backend ALB Target Group ARN. FastCollector의 ALB 조회 1차 기준 |
| `fast.backend_runtime.alb.target_group_arn` | ALB health/metric을 조회한 Target Group ARN. 정상 수집 시 ECS `targetGroupArn`과 일치 |
| `fast.backend_runtime.alb.unhealthy_host_count` | ALB target state가 실제 `unhealthy`인 target 수. `draining`은 포함하지 않음 |
| `fast.backend_runtime.alb.draining_host_count` | ECS 배포/scale-in 등으로 deregistration 중인 ALB target 수 |
| `fast.data_pipeline` | Lambda, DynamoDB, EventBridge Scheduler 상태 |
| `fast.factory_freshness` | factory별 pipeline freshness/risk 요약 |
| `slow.eks_management` | EKS cluster/nodegroup/ASG, Kubernetes node/pod, ArgoCD 상태 |
| `slow.storage_freshness` | factory별 S3 raw/processed/processed_agg latest object time |

Dashboard/API는 Cloud infra 현재 상태를 이 item에서 읽는다. Backend는 CloudWatch, EKS, Kubernetes API, S3를 직접 반복 조회하지 않는다.

## 환경 데이터와 노드 상태 데이터 분리

### 환경 데이터

source type:

```text
factory_state
```

주기:

```text
3초
```

저장:

| 저장소 | 저장 방식 | 용도 |
| --- | --- | --- |
| `DynamoDB LATEST.factory_state` | 3초마다 overwrite | 현재 환경 상태 카드 |
| `DynamoDB LATEST.risk` | 3초마다 overwrite | 현재 Risk 카드 |
| `DynamoDB HISTORY#STATE` | LATEST snapshot + TTL | 온도/습도/기압/AI score/Risk 그래프 |
| `DynamoDB GRAPH#5M` | 5분 집계 + TTL | Dashboard 그래프 기본 read model |
| `S3 raw` | 3초 원본 전체 | 원본 보존 |
| `S3 processed` | 3초 계산 결과 | 장기 이력/재처리 |
| `S3 processed_agg` | 5분 집계 결과 | 장기 그래프 보조 조회 |

### 노드 상태 데이터

source type:

```text
infra_state
```

주기:

```text
20초
```

저장:

| 저장소 | 저장 방식 | 용도 |
| --- | --- | --- |
| `DynamoDB LATEST.infra_state` | 20초마다 overwrite | 현재 노드/워크로드/장치 상태 |
| `DynamoDB LATEST.pipeline_status` | 20초 수신 또는 1분 refresh마다 overwrite | 현재 파이프라인 상태 |
| `DynamoDB HISTORY#STATE` | LATEST snapshot + TTL | 노드 CPU/memory/disk/Ready 그래프 |
| `DynamoDB GRAPH#5M` | 5분 집계 + TTL | Dashboard 그래프 기본 read model |
| `S3 raw` | 20초 원본 전체 | 장애 분석/원본 보존 |
| `S3 processed` | 20초 상태 요약 | 운영 이력/리포트 |

## Dashboard 조회 기준

Dashboard page와 Dashboard VPC 구현은 별도 담당 범위다. 아래 기준은 해당 구현이 조회할 데이터 계약이며, 이 repo에서는 DynamoDB/S3 processed 쪽 read model을 유지한다.

| 화면 요소 | 기본 조회 저장소 | 설명 |
| --- | --- | --- |
| 공장별 현재 Risk 카드 | `DynamoDB LATEST` | score, level, top causes |
| 현재 환경 상태 | `DynamoDB LATEST.factory_state` | 온도, 습도, 기압, AI score |
| 현재 노드 상태 | `DynamoDB LATEST.infra_state` | Ready, CPU, memory, disk |
| 현재 pipeline 상태 | `DynamoDB LATEST.pipeline_status` | normal/warning/critical |
| Cloud infra 현재 상태 | `DynamoDB CLOUD#infra/LATEST` | Backend/API, data pipeline, EKS, ArgoCD, S3 freshness |
| 최근 Risk 그래프 | `DynamoDB GRAPH#5M` | 5분 risk score 집계 |
| 최근 환경 그래프 | `DynamoDB GRAPH#5M` | 5분 sensor 집계 |
| 최근 노드 그래프 | `DynamoDB GRAPH#5M` | 5분 infra 집계 |
| 상세 이력 drill-down | `DynamoDB HISTORY#STATE` | raw snapshot 수준의 단기 상세 조회 |
| 장기 이력/감사 | `S3 processed`, `S3 processed_agg`, `S3 raw` | 장기 조회, 재처리, 리포트 |

Dashboard API 예시:

```text
GET /factories
  -> DynamoDB LATEST list/query

GET /factories/{factory_id}
  -> DynamoDB LATEST get item

GET /factories/{factory_id}/risk-history?window=1h
  -> DynamoDB GRAPH#5M query, risk.score 집계 필드 추출

GET /factories/{factory_id}/factory-history?window=1h
  -> DynamoDB GRAPH#5M query, sensor 집계 필드 추출

GET /factories/{factory_id}/infra-history?window=1h
  -> DynamoDB GRAPH#5M query, infra 집계 필드 추출

GET /factories/{factory_id}/state-snapshots?window=15m
  -> DynamoDB HISTORY#STATE query, 상세 snapshot 추출

GET /cloud-infra/status
  -> DynamoDB GetItem pk=CLOUD#infra sk=LATEST
```

## 구현 기준

- Lambda는 `message_id` 기준으로 idempotent하게 처리한다.
- `S3 raw` 저장은 IoT Rule이 담당한다.
- Lambda는 `DynamoDB LATEST`, `DynamoDB HISTORY#STATE`, `S3 processed`를 담당한다.
- DataProcessor refresh schedule은 새 메시지가 없는 factory의 `pipeline_status`와 `risk`가 stale 값으로 남지 않도록 1분마다 LATEST/HISTORY/S3 state_snapshot을 갱신한다.
- GraphAggregator5m은 `DynamoDB HISTORY#STATE`를 읽고 `DynamoDB GRAPH#5M`, `S3 processed_agg`를 담당한다.
- CloudInfraFastCollector1m은 `DynamoDB CLOUD#infra/LATEST.fast`, `HISTORY#FAST`, `S3 processed/cloud_infra/fast`를 담당한다.
- CloudInfraSlowCollector5m은 `DynamoDB CLOUD#infra/LATEST.slow`, `HISTORY#SLOW`, `S3 processed/cloud_infra/slow`를 담당한다.
- Dashboard current state는 S3 `latest/` prefix가 아니라 DynamoDB LATEST를 기준으로 조회한다.
- Cloud infra dashboard current state는 `CLOUD#infra/LATEST`를 기준으로 조회한다.
- `DynamoDB HISTORY#STATE`는 갱신된 `LATEST`와 같은 구조를 저장하고 TTL만 추가한다.
- `DynamoDB GRAPH#5M`은 최근 그래프의 기본 read model이다.
- `S3 processed state_snapshot`은 `DynamoDB HISTORY#STATE`와 같은 구조를 저장하되 TTL은 제외한다.
- `S3 processed_agg metrics_5m`은 `DynamoDB GRAPH#5M`과 같은 graph aggregate를 저장하되 TTL은 제외한다.
- `DynamoDB HISTORY#STATE`와 `DynamoDB GRAPH#5M`에는 TTL을 적용한다.
- 장기 보존과 재처리는 DynamoDB가 아니라 S3 raw/processed를 기준으로 한다.
- Dashboard는 기본적으로 DynamoDB를 조회하고, 상세/감사/장기 이력에서만 S3를 조회한다.
