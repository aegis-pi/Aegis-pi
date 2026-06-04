# Data Pipeline 구현 레퍼런스

상태: 구현 기준 source of truth
기준일: 2026-06-04
관련 스펙: `docs/specs/data_storage_pipeline.md`

---

## 개요

Aegis 데이터 파이프라인은 Edge factory에서 발생한 센서·인프라 데이터를 AWS IoT Core로 수신한 뒤 Lambda가 정규화·위험도 계산을 수행하고 DynamoDB와 S3에 이중 저장하는 구조다.

- **실시간 현황 조회** → DynamoDB LATEST
- **최근 그래프 조회** → DynamoDB GRAPH#5M
- **상세 이력 조회** → DynamoDB HISTORY#STATE
- **장기 보존·재처리** → S3 processed / raw

2026-06-04 기준 `factory-a/b/c` IoT -> Lambda -> DynamoDB/S3 processed 적재, `risk-v0.2.0` Risk Score 계산, DataProcessor 1분 freshness refresh, GraphAggregator5m의 DynamoDB `GRAPH#5M` 및 S3 `processed_agg` 집계는 검증 완료 상태다. 추가로 CloudInfraFastCollector1m/SlowCollector5m이 `CLOUD#infra/LATEST`, `HISTORY#FAST`, `HISTORY#SLOW`, S3 `processed/cloud_infra/` snapshot을 저장한다. RiskAlertDispatcher는 S3 `processed/` ObjectCreated 이벤트를 받아 factory state_snapshot 및 cloud infra fast/slow snapshot의 warning/danger 조건을 Slack으로 알린다. Cloud alert는 specific 원인을 우선하고 같은 원인을 포괄하는 generic section alert는 fallback으로만 사용한다. `configs/runtime/runtime-config.yaml`은 아직 Lambda Risk 계산에 연결되지 않았으며, 다음 고도화는 runtime config 기반 weight/threshold/factory override 적용과 Risk Twin read model 안정화다.

---

## 전체 플로우

```text
Edge Devices
  - factory-a-log-adapter
  - dummy-data-generator
  -> edge-iot-publisher
  -> AWS IoT Core topic: aegis/{factory_id}/{source_type}
      -> IoT Topic Rule AEGIS_IoTRule_factory_{a,b,c}_raw_s3
          -> S3 raw/{factory_id}/{source_type}/...
          -> Lambda AEGIS-Lambda-DataProcessor
              -> DynamoDB LATEST
                 pk = FACTORY#{factory_id}
                 sk = LATEST
              -> DynamoDB HISTORY#STATE
                 pk = FACTORY#{factory_id}
                 sk = HISTORY#STATE#{updated_at}
                 ttl = HISTORY_TTL_HOURS 기준
              -> S3 processed/{factory_id}/{dataset}/...
```

5분 그래프 집계는 data processor 저장 이후 별도 Lambda가 수행한다.

```text
EventBridge Scheduler (rate 5 minutes)
  -> Lambda: AEGIS-Lambda-GraphAggregator5m
      -> Query DynamoDB HISTORY#STATE by factory/time window
      -> PutItem DynamoDB GRAPH#5M#{bucket_start}
      -> PutObject S3 processed_agg/{factory_id}/metrics_5m/...
```

Cloud infra dashboard read model은 별도 collector 2개가 수행한다.

`CLOUD#infra`의 `fast.factory_freshness`는 factory 상태를 함께 조회하기 위한 대시보드 참고 데이터로 유지한다.
2026-06-04 AWS 배포본 기준 Cloud `overall_status`는 `backend_runtime`, `datastores`,
`data_pipeline`, `factory_freshness`, `eks_management`, `storage_freshness`를 함께 사용한다.

```text
EventBridge Scheduler (rate 1 minute)
  -> Lambda: AEGIS-Lambda-CloudInfraFastCollector
      -> ECS/ALB/CloudFront/Redis/RDS/Lambda/DynamoDB/Scheduler/SQS DLQ/factory freshness 조회
         - ALB Target Group은 ALB_TARGET_GROUP_NAME 이름으로 조회
      -> PutItem DynamoDB CLOUD#infra / LATEST.fast
      -> PutItem DynamoDB HISTORY#FAST#{updated_at} (TTL 6h)
      -> PutObject S3 processed/cloud_infra/fast/...

EventBridge Scheduler (rate 5 minutes)
  -> Lambda: AEGIS-Lambda-CloudInfraSlowCollector
      -> EKS/Kubernetes/ArgoCD/S3 freshness 조회
      -> PutItem DynamoDB CLOUD#infra / LATEST.slow
      -> PutItem DynamoDB HISTORY#SLOW#{updated_at} (TTL 24h)
      -> PutObject S3 processed/cloud_infra/slow/...
```

데이터가 완전히 끊긴 공장은 새 IoT 메시지가 없으므로 일반 메시지 처리만으로는 `LATEST`가 갱신되지 않는다. 이를 보정하기 위해 DataProcessor refresh 스케줄이 별도로 동작한다.

```text
EventBridge Scheduler (rate 1 minute)
  -> Lambda: AEGIS-Lambda-DataProcessor
     payload: {"action":"refresh_pipeline_status","factories":["factory-a","factory-b","factory-c"]}
      -> GetItem DynamoDB LATEST
      -> 현재 시각 기준 pipeline_status 재계산
      -> 최신 factory_state / infra_state / pipeline_status로 risk 재계산
      -> UpdateItem DynamoDB LATEST
      -> PutItem DynamoDB HISTORY#STATE
      -> PutObject S3 processed/{factory_id}/state_snapshot/...
```

Alert dispatching은 processed snapshot 저장 뒤 S3 event로 동작한다.

```text
S3 ObjectCreated
  prefixes:
    processed/factory-a/state_snapshot/
    processed/factory-b/state_snapshot/
    processed/factory-c/state_snapshot/
    processed/cloud_infra/fast/
    processed/cloud_infra/slow/
  -> Lambda: AEGIS-Lambda-RiskAlertDispatcher
      -> GetObject S3 processed snapshot
      -> warning/danger rule evaluate
         cloud specific alert 우선, generic section alert는 fallback
         일부 warning은 연속 관측 확인 후 전송
      -> DynamoDB UpdateItem ALERT#{scope} / {severity}#{reason}#{status}
         cooldown + stale snapshot dedupe
      -> Secrets Manager GetSecretValue
      -> Slack webhook routing
         cloud-infra -> cloud channel
         factory-a/b/c -> factory별 channel
```

---

## source_type별 처리 플로우

### factory_state (3초 주기)

```
  IoT 메시지 수신  source_type: factory_state
                │
                ▼
       ┌─────────────────────┐
       │   envelope 파싱·검증 │  schema_version, factory_id,
       │                     │  message_id, source_type 확인
       └──────────┬──────────┘
                  │
                  ▼
       ┌─────────────────────────────┐
       │  normalize_factory_state()  │  sensor avg(온도·습도·기압)
       │                             │  AI score(fire·fall·bend)
       └──────────┬──────────────────┘
                  │
                  ▼
       ┌─────────────────────────────┐
       │  calc_risk()                │  최신 infra_state와
       │                             │  pipeline_status까지 함께 반영
       └──────────┬──────────────────┘
                  │
                  ▼
       ┌─────────────────────────────┐
       │  DynamoDB GetItem           │  LATEST.last_infra_state_at
       │  (last_infra_state_at 조회) │  → 없으면 None 반환
       └──────────┬──────────────────┘
                  │
                  ▼
       ┌─────────────────────────────┐
       │  calc_pipeline_status()     │  경과 ≤40s → normal
       │                             │  40s~60s   → warning
       │                             │  >60s / None → critical
       └──────────┬──────────────────┘
                  │
       ┌──────────┴──────────────────────────────────────────┐
       │  DynamoDB 쓰기 (2건)        S3 processed 쓰기 (3건) │
       │                                                     │
       │  ┌──────────────────────┐  ┌──────────────────────┐ │
       │  │ UpdateItem LATEST    │  │ PutObject            │ │
       │  │ factory_state        │  │ factory_state/...    │ │
       │  │ + risk               │  │ normalized sensor    │ │
       │  │ + pipeline_status    │  └──────────────────────┘ │
       │  └──────────────────────┘                           │
       │  ┌──────────────────────┐  ┌──────────────────────┐ │
       │  │ PutItem              │  │ PutObject            │ │
       │  │ HISTORY#STATE#{ts}   │  │ risk_score/...       │ │
       │  │ LATEST snapshot      │  │ normalized + risk    │ │
       │  │ + ttl                │  │ + pipeline_status    │ │
       │  └──────────────────────┘  ┌──────────────────────┐ │
       │                            │ PutObject            │ │
       │                            │ state_snapshot/...   │ │
       │                            │ LATEST snapshot      │ │
       │                            │ without ttl          │ │
       │                            └──────────────────────┘ │
       └─────────────────────────────────────────────────────┘
```

### infra_state (20초 주기)

```
  IoT 메시지 수신  source_type: infra_state
                │
                ▼
       ┌─────────────────────┐
       │   envelope 파싱·검증 │
       └──────────┬──────────┘
                  │
                  ▼
       ┌─────────────────────────────┐
       │  normalize_infra_state()    │  cluster · nodes · workloads
       │                             │  devices · heartbeat 추출
       └──────────┬──────────────────┘
                  │
                  ▼
       ┌─────────────────────────────┐
       │  calc_pipeline_status()     │  source_timestamp 기준
       │                             │  (수신 직후이므로 age ≈ 0)
       └──────────┬──────────────────┘
                  │
       ┌──────────┴──────────────────────────────────────────┐
       │  DynamoDB 쓰기 (2건)        S3 processed 쓰기 (2건) │
       │                                                     │
       │  ┌──────────────────────┐  ┌──────────────────────┐ │
       │  │ UpdateItem LATEST    │  │ PutObject            │ │
       │  │ infra_state          │  │ infra_state/...      │ │
       │  │ + pipeline_status    │  │ normalized           │ │
       │  │ last_infra_state_at  │  │ + pipeline_status    │ │
       │  │ 갱신                 │  └──────────────────────┘ │
       │  └──────────────────────┘                           │
       │  ┌──────────────────────┐                           │
       │  │ PutItem              │                           │
       │  │ HISTORY#STATE#{ts}   │                           │
       │  │ LATEST snapshot      │                           │
       │  │ + ttl                │                           │
       │  └──────────────────────┘  ┌──────────────────────┐ │
       │                            │ PutObject            │ │
       │                            │ state_snapshot/...   │ │
       │                            │ LATEST snapshot      │ │
       │                            │ without ttl          │ │
       │                            └──────────────────────┘ │
       └─────────────────────────────────────────────────────┘
```

---

## DynamoDB 저장 구조

```text
Table: AEGIS-DynamoDB-FactoryStatus
pk = FACTORY#{factory_id}   (factory-a / factory-b / factory-c)

sk = LATEST
  - TTL 없음
  - factory_state / infra_state / risk / pipeline_status 최신 상태
  - 3초 또는 20초 수신 주기에 따라 부분 갱신

sk = HISTORY#STATE#{updated_at}
  - TTL 있음
  - LATEST와 같은 구조 + ttl
  - factory_state 또는 infra_state 수신마다 신규 snapshot 저장

sk = GRAPH#5M#{bucket_start}
  - TTL 있음
  - 5분 bucket sensor / risk / AI / infra 집계

pk = CLOUD#infra
sk = LATEST
  - TTL 없음
  - Cloud infra dashboard 현재 상태 1건
  - FastCollector가 fast 필드, SlowCollector가 slow 필드를 부분 갱신

sk = HISTORY#FAST#{updated_at}
  - TTL 6시간
  - 1분 fast cloud infra snapshot

sk = HISTORY#SLOW#{updated_at}
  - TTL 24시간
  - 5분 slow cloud infra snapshot

pk = ALERT#{scope}
sk = {severity}#{reason}#{status}
  - TTL 있음
  - RiskAlertDispatcher cooldown/dedupe 상태
  - scope 예: cloud-infra, factory-a, factory-b, factory-c
  - last_source_updated_at보다 오래된 snapshot 또는 cooldown 중인 동일 조건은 Slack 재전송 skip

HISTORY#STATE, GRAPH#5M, HISTORY#FAST, HISTORY#SLOW, ALERT# item은 ttl 값에 따라 DynamoDB TTL로 자동 삭제된다.
LATEST와 CLOUD#infra/LATEST는 삭제되지 않고 계속 overwrite된다.
```

---

## S3 버킷 구조

```text
aegis-bucket-data/
├── raw/                              ← IoT Rule이 직접 저장 (원본, 가공 없음)
│   ├── factory-a/
│   │   ├── factory_state/yyyy=2026/mm=05/dd=21/{message_id}.json
│   │   └── infra_state/yyyy=2026/mm=05/dd=21/{message_id}.json
│   ├── factory-b/  (동일 구조)
│   └── factory-c/  (동일 구조)
│
├── processed/                        ← Lambda가 저장 (정규화·계산 결과)
│   ├── factory-a/
│   │   ├── factory_state/yyyy=2026/mm=05/dd=21/hh=10/{message_id}.json
│   │   ├── risk_score/yyyy=2026/mm=05/dd=21/hh=10/{message_id}.json
│   │   ├── infra_state/yyyy=2026/mm=05/dd=21/hh=10/{message_id}.json
│   │   └── state_snapshot/yyyy=2026/mm=05/dd=21/hh=10/{updated_at}.json
│   ├── factory-b/  (동일 구조)
│   ├── factory-c/  (동일 구조)
│   └── cloud_infra/
│       ├── fast/yyyy=2026/mm=06/dd=01/hh=15/2026-06-01T15-30-00Z.json
│       └── slow/yyyy=2026/mm=06/dd=01/hh=15/2026-06-01T15-30-00Z.json
│
└── processed_agg/                    ← GraphAggregator5m이 저장 (그래프 집계)
    ├── factory-a/metrics_5m/yyyy=2026/mm=05/dd=21/hh=10/mm=05.json
    ├── factory-b/  (동일 구조)
    └── factory-c/  (동일 구조)

raw/        → 90일 후 Glacier Instant Retrieval 전환 (S3 Lifecycle)
processed/  → 365일 후 Standard-IA 전환 (S3 Lifecycle)
```

---

## Risk 계산 구조

```text
입력:
  - 최신 factory_state
  - 최신 infra_state
  - 최신 pipeline_status

weighted contribution:
  base_score = 100 - sum(weight * severity)

gate cap:
  - danger gate가 있으면 최종 score <= 49
  - warning gate가 있으면 최종 score <= 84
  - nodes_all_not_ready는 최종 score = 0

level:
  - 85~100: safe
  - 50~84: warning
  - 0~49: danger
```

`risk-v0.2.0` 가중치:

| Field | Weight | 입력 |
|---|---:|---|
| `temperature` | 10 | factory_state |
| `humidity` | 5 | factory_state |
| `pressure` | 5 | factory_state |
| `ai_event_rate` | 15 | factory_state |
| `node_status` | 20 | infra_state |
| `pod_health` | 15 | infra_state |
| `device_availability` | 10 | infra_state |
| `data_freshness` | 10 | pipeline_status |
| `storage_pressure` | 5 | infra_state |
| `network_reachability` | 5 | infra_state |

Risk 출력은 `score`, `base_score`, `level`, `base_level`, `top_causes`, `gates`, `calculation_version`, `calculated_at`을 포함한다.

---

## Pipeline Status 판정

```
  factory_state 수신 시:
    DynamoDB LATEST에서 last_infra_state_at 읽기
    → 현재 시각(UTC)과의 차이(age) 계산

  age (초)
     0          40          60                  ∞
     ├──────────┼───────────┼───────────────────►
     │  normal  │  warning  │     critical       │

  last_infra_state_at 없음 (최초 수신) → critical

  ──────────────────────────────────────────────
  infra_state 수신 시:
    source_timestamp ≈ now  →  age ≈ 0  →  항상 normal

  ──────────────────────────────────────────────
  refresh schedule 실행 시:
    IoT 메시지가 없어도 1분마다 LATEST.last_infra_state_at 기준으로 재계산
    stale 상태가 되면 pipeline_status critical + risk 재계산
```

2026-05-29 배포 검증:

```text
factory-a 마지막 입력:
- last_factory_state_at = 2026-05-28T07:54:39Z
- last_infra_state_at = 2026-05-28T07:54:31Z

DataProcessor refresh 후:
- pipeline_status.status = critical
- latest_infra_state_age_seconds > 82000
- risk.score = 0
- risk.level = danger
- gates = nodes_all_not_ready, pipeline_status_critical
- S3 state_snapshot 신규 생성 확인
```

---

## Factory-A Node Metric 수집

`factory-a-log-adapter`는 Kubernetes API로 node/workload/device 상태를 읽고, Prometheus HTTP API로 node exporter 사용률 지표를 조회한다.

기본 Prometheus endpoint:

```text
http://prometheus-svc.monitoring.svc.cluster.local:9090
```

사용하는 Prometheus metric:

| 필드 | Prometheus 기준 |
|---|---|
| `cpu_usage_percent` | `node_cpu_seconds_total{mode="idle"}`의 2분 rate 기반 |
| `memory_usage_percent` | `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes` |
| `disk_usage_percent` | root filesystem `node_filesystem_avail_bytes / node_filesystem_size_bytes` |

`node_uname_info`의 `instance -> nodename` 매핑을 우선 사용해 Prometheus series를 canonical `node_id`에 연결한다. Prometheus 조회 실패 또는 해당 node series 누락 시 사용률 필드는 `null`로 둔다. `0`은 실제 0% 사용률을 의미해야 하므로 미수집 값을 `0`으로 대체하지 않는다.

---

## AWS 리소스 목록

| 리소스 | 이름 | 설정 |
|---|---|---|
| Lambda Function | `AEGIS-Lambda-DataProcessor` | python3.12, 512MB, timeout 60s |
| Lambda IAM Role | `AEGIS-IAMRole-Lambda-DataProcessor` | DynamoDB GetItem/PutItem/UpdateItem, S3 PutObject processed/* |
| Lambda IAM Policy | `AEGIS-IAMPolicy-Lambda-DataProcessor` | CloudWatch Logs + DynamoDB + S3 |
| CloudWatch Log Group | `/aws/lambda/AEGIS-Lambda-DataProcessor` | 보존 30일 |
| EventBridge Scheduler | `AEGIS-Schedule-DataProcessorRefresh1m` | rate(1 minute), DataProcessor freshness refresh 호출 |
| Scheduler IAM Role | `AEGIS-IAMRole-Scheduler-DataProcessorRefresh` | DataProcessor Lambda InvokeFunction |
| Lambda Function | `AEGIS-Lambda-GraphAggregator5m` | python3.12, 512MB, timeout 60s |
| Lambda Function | `AEGIS-Lambda-CloudInfraFastCollector` | python3.12, 1분 cloud infra fast read model |
| Lambda Function | `AEGIS-Lambda-CloudInfraSlowCollector` | python3.12, 5분 cloud infra slow read model |
| Lambda Function | `AEGIS-Lambda-RiskAlertDispatcher` | python3.12, S3 processed snapshot warning/danger Slack alert |
| EventBridge Scheduler | `AEGIS-Schedule-GraphAggregator5m` | rate(5 minutes), GraphAggregator5m 호출 |
| EventBridge Scheduler | `AEGIS-Schedule-CloudInfraFastCollector1m` | rate(1 minute), FastCollector 호출 |
| EventBridge Scheduler | `AEGIS-Schedule-CloudInfraSlowCollector5m` | rate(5 minutes), SlowCollector 호출 |
| CloudWatch Log Group | `/aws/lambda/AEGIS-Lambda-GraphAggregator5m` | 보존 30일 |
| CloudWatch Log Group | `/aws/lambda/AEGIS-Lambda-RiskAlertDispatcher` | 보존 30일 |
| S3 Bucket Notification | `aegis-bucket-data` processed prefixes | RiskAlertDispatcher ObjectCreated trigger |
| Secrets Manager | `AEGIS/foundation-mvp/risk-alert/slack-webhook-url` | cloud/default Slack webhook URL value, build script가 값 주입 |
| Secrets Manager | `AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-a,b,c` | factory별 Slack webhook URL value, build script가 값 주입 |
| DynamoDB Table | `AEGIS-DynamoDB-FactoryStatus` | PAY_PER_REQUEST, PITR 활성화, Streams NEW_AND_OLD_IMAGES |
| IoT Rule (factory-a) | `AEGIS_IoTRule_factory_a_raw_s3` | S3 + Lambda 액션 |
| IoT Rule (factory-b) | `AEGIS_IoTRule_factory_b_raw_s3` | S3 + Lambda 액션 |
| IoT Rule (factory-c) | `AEGIS_IoTRule_factory_c_raw_s3` | S3 + Lambda 액션 |
| IoT Rule IAM Role | `AEGIS-IAMRole-IoTRule-S3` | S3 raw/factory-a,b,c/* PutObject |

### Lambda 환경 변수

| 변수 | 값 (Terraform 주입) |
|---|---|
| `DYNAMODB_TABLE_NAME` | `AEGIS-DynamoDB-FactoryStatus` |
| `FACTORY_IDS` | `factory-a,factory-b,factory-c` |
| `S3_BUCKET_NAME` | `aegis-bucket-data` |
| `HISTORY_TTL_HOURS` | `var.dynamodb_history_ttl_hours` |

### GraphAggregator5m 환경 변수

| 변수 | 값 (Terraform 주입) |
|---|---|
| `DYNAMODB_TABLE_NAME` | `AEGIS-DynamoDB-FactoryStatus` |
| `S3_BUCKET_NAME` | `aegis-bucket-data` |
| `FACTORY_IDS` | `factory-a,factory-b,factory-c` |
| `BUCKET_MINUTES` | `5` |
| `LOOKBACK_BUCKETS` | `1` |
| `GRAPH_TTL_HOURS` | `48` |
| `EXPECTED_SAMPLE_INTERVAL_SECONDS` | `3` |
| `AI_SCORE_THRESHOLD` | `0.7` |
| `S3_OUTPUT_PREFIX` | `processed_agg` |

### RiskAlertDispatcher 환경 변수

| 변수 | 값 (Terraform 주입) |
|---|---|
| `DYNAMODB_TABLE_NAME` | `AEGIS-DynamoDB-FactoryStatus` |
| `ALERT_STATE_TTL_SECONDS` | alert dedupe state TTL seconds |
| `SLACK_HTTP_TIMEOUT_SECONDS` | Slack webhook HTTP timeout |
| `SLACK_WEBHOOK_SECRET_CLOUD` | cloud/default Secrets Manager ARN |
| `SLACK_WEBHOOK_SECRET_FACTORY_A` | factory-a Secrets Manager ARN |
| `SLACK_WEBHOOK_SECRET_FACTORY_B` | factory-b Secrets Manager ARN |
| `SLACK_WEBHOOK_SECRET_FACTORY_C` | factory-c Secrets Manager ARN |
| `COOLDOWN_FACTORY_STATE_SNAPSHOT_WARNING_SECONDS` | factory warning cooldown |
| `COOLDOWN_FACTORY_STATE_SNAPSHOT_DANGER_SECONDS` | factory danger cooldown |
| `COOLDOWN_CLOUD_INFRA_FAST_WARNING_SECONDS` | cloud fast warning cooldown |
| `COOLDOWN_CLOUD_INFRA_FAST_DANGER_SECONDS` | cloud fast danger cooldown |
| `COOLDOWN_CLOUD_INFRA_SLOW_WARNING_SECONDS` | cloud slow warning cooldown |
| `COOLDOWN_CLOUD_INFRA_SLOW_DANGER_SECONDS` | cloud slow danger cooldown |

---

## S3 processed 오브젝트 포맷

### factory_state

```json
{
  "source_message_id": "factory-a:factory_state:worker2:2026-05-21T10:00:03Z",
  "factory_id": "factory-a",
  "source_timestamp": "2026-05-21T10:00:03Z",
  "processed_at": "2026-05-21T10:00:03Z",
  "data": {
    "aggregation_window_seconds": 3,
    "temperature_celsius": 28.5,
    "humidity_percent": 65.0,
    "pressure_hpa": 1012.3,
    "sample_count": 5,
    "fire_score": 0.02,
    "fall_score": 0.0,
    "bend_score": 0.01,
    "abnormal_sound": "none",
    "ai_sample_count": 3
  }
}
```

### risk_score

```json
{
  "source_message_id": "factory-a:factory_state:worker2:2026-05-21T10:00:03Z",
  "factory_id": "factory-a",
  "source_timestamp": "2026-05-21T10:00:03Z",
  "processed_at": "2026-05-21T10:00:03Z",
  "data": { "...factory_state data와 동일..." },
  "risk": {
    "score": 72.14,
    "level": "warning",
    "top_causes": [
      { "field": "temperature", "value": 35.2, "contribution": 22.86 },
      { "field": "humidity", "value": 73.0, "contribution": 5.0 }
    ]
  },
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 12
  }
}
```

### infra_state

```json
{
  "source_message_id": "factory-a:infra_state:cluster:2026-05-21T10:00:20Z",
  "factory_id": "factory-a",
  "source_timestamp": "2026-05-21T10:00:20Z",
  "processed_at": "2026-05-21T10:00:20Z",
  "data": {
    "agent_status": "running",
    "cluster_name": "factory-a",
    "kubernetes_version": "v1.29.0",
    "nodes_total": 3,
    "nodes_ready": 3,
    "pods_ready": 12,
    "pods_total": 12,
    "nodes": [...],
    "workloads": [...],
    "devices": { "bme280": { "status": "ok" } }
  },
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 1
  }
}
```

### state_snapshot

DynamoDB `HISTORY#STATE`와 같은 전체 상태 snapshot이다. S3에서는 DynamoDB TTL 정책 필드인 `ttl`을 저장하지 않는다.

```json
{
  "pk": "FACTORY#factory-a",
  "sk": "HISTORY#STATE#2026-05-21T10:00:03.123Z",
  "factory_id": "factory-a",
  "schema_version": "0.1.0",
  "factory_state": {
    "message_id": "factory-a:factory_state:worker2:2026-05-21T10:00:03Z",
    "source_timestamp": "2026-05-21T10:00:03Z",
    "temperature_celsius": 28.5,
    "humidity_percent": 65.0,
    "pressure_hpa": 1012.3
  },
  "infra_state": {
    "message_id": "factory-a:infra_state:cluster:2026-05-21T10:00:00Z",
    "source_timestamp": "2026-05-21T10:00:00Z",
    "nodes_total": 3,
    "nodes_ready": 3
  },
  "risk": {
    "score": 91.2,
    "level": "safe"
  },
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 3
  },
  "last_factory_state_at": "2026-05-21T10:00:03Z",
  "last_infra_state_at": "2026-05-21T10:00:00Z",
  "updated_at": "2026-05-21T10:00:03.123Z"
}
```

### processed_agg metrics_5m

GraphAggregator5m이 DynamoDB `HISTORY#STATE`를 5분 bucket으로 집계한 S3 보조 산출물이다. S3 body에서는 DynamoDB TTL 정책 필드인 `ttl`을 제외하고, 원래 DynamoDB key는 `dynamodb_pk`, `dynamodb_sk`로 남긴다.

```json
{
  "dynamodb_pk": "FACTORY#factory-a",
  "dynamodb_sk": "GRAPH#5M#2026-05-21T10:05:00Z",
  "factory_id": "factory-a",
  "schema_version": "graph-5m-v0.1.0",
  "bucket_minutes": 5,
  "bucket_start": "2026-05-21T10:05:00Z",
  "bucket_end": "2026-05-21T10:09:59.999Z",
  "sensor": {
    "temperature_celsius": {
      "unit": "celsius",
      "count": 100,
      "min": 24.0,
      "max": 31.2,
      "mean": 27.4
    }
  },
  "risk": {
    "score": {
      "unit": "score",
      "count": 100,
      "min": 88.0,
      "max": 99.0,
      "mean": 93.2
    }
  },
  "infra": {
    "cpu_usage_percent": {
      "unit": "percent",
      "count": 15,
      "mean": 42.1
    },
    "nodes": [
      {
        "node_id": "worker1",
        "cpu_usage_percent": {
          "unit": "percent",
          "count": 15,
          "mean": 38.2
        },
        "memory_usage_percent": {
          "unit": "percent",
          "count": 15,
          "mean": 61.4
        },
        "disk_usage_percent": {
          "unit": "percent",
          "count": 15,
          "mean": 43.0
        }
      }
    ]
  },
  "quality": {
    "source_dataset": "DynamoDB HISTORY#STATE",
    "source_count": 100,
    "expected_count": 100,
    "collection_rate": 1.0
  }
}
```

---

## DynamoDB 키 패턴 요약

| SK | 저장 계기 | 주기 | TTL | 내용 |
|---|---|---|---|---|
| `LATEST` | factory_state / infra_state 수신 | 3초 / 20초 덮어씀 | 없음 | 최신 전체 상태 |
| `HISTORY#STATE#{updated_at}` | factory_state / infra_state 수신 또는 1분 refresh | 3초 / 20초 / 1분 | `HISTORY_TTL_HOURS` | LATEST와 같은 구조 + ttl |
| `GRAPH#5M#{bucket_start}` | GraphAggregator5m 실행 | 5분 | `GRAPH_TTL_HOURS` | 5분 그래프 집계 |
| `{severity}#{reason}#{status}` under `ALERT#{scope}` | RiskAlertDispatcher alert reserve | event driven | `ALERT_STATE_TTL_SECONDS` | Slack cooldown/dedupe state |

> `pk`는 모두 `FACTORY#{factory_id}` 고정.
> Cloud infra는 `pk=CLOUD#infra`, alert dedupe는 `pk=ALERT#{scope}`를 사용한다.

---

## Dashboard 읽기 경로

```
  Dashboard 요청
       │
       ├── 현재 상태 카드 (Risk / 환경 / 노드 / Pipeline)
       │        └── DynamoDB GetItem  FACTORY#{id} / LATEST
       │
         ├── Risk 추이 그래프
         │        └── DynamoDB Query   pk=FACTORY#{id}
         │                             sk begins_with "GRAPH#5M#"
         │                             risk.score 집계 필드 추출
         │
         ├── 환경 데이터 그래프 (온도·습도 등)
         │        └── DynamoDB Query   pk=FACTORY#{id}
         │                             sk begins_with "GRAPH#5M#"
         │                             sensor 집계 필드 추출
         │
         ├── 인프라 상태 그래프 (CPU·memory·nodes)
         │        └── DynamoDB Query   pk=FACTORY#{id}
         │                             sk begins_with "GRAPH#5M#"
         │                             infra 집계 필드 추출
       │
       └── 장기 이력 / 감사 / 재처리
                └── S3 prefix scan   processed/{factory_id}/...
                                     raw/{factory_id}/...
```

---

## 데이터 보존 기간 요약

| 저장소 | 보존 기간 | 방식 |
|---|---|---|
| DynamoDB LATEST | 무기한 | overwrite |
| DynamoDB HISTORY#STATE | `HISTORY_TTL_HOURS` | TTL 자동 삭제 |
| DynamoDB GRAPH#5M | `GRAPH_TTL_HOURS` | TTL 자동 삭제 |
| S3 raw | 90일 후 Glacier IR 전환 | S3 Lifecycle |
| S3 processed | 365일 후 Standard-IA 전환 | S3 Lifecycle |
| CloudWatch Logs | 30일 | Log Group retention |

---

## 관측 확장 범위

현재 data-pipeline 완료 판정은 S3 raw/processed/processed_agg, DynamoDB LATEST/HISTORY#STATE/GRAPH#5M, Lambda, IoT Rule, EventBridge Scheduler 실제 리소스 확인을 기준으로 한다. 후속 확장에서는 운영 중 지연과 처리 품질을 지속적으로 보기 위해 CloudWatch metric과 Grafana 관측 패널을 추가한다.

### 역할 분리

| 관측 대상 | 수집/조회 경로 | 설명 |
|---|---|---|
| Lambda 기본 지표 | CloudWatch Metrics | Invocations, Errors, Duration, Throttles, ConcurrentExecutions |
| DynamoDB 기본 지표 | CloudWatch Metrics | SuccessfulRequestLatency, ThrottledRequests, ConsumedRead/WriteCapacityUnits, SystemErrors |
| S3 요청 지표 | CloudWatch Metrics | prefix 단위 request/error/latency. 비용을 보고 필요한 prefix만 활성화 |
| IoT Rule 실행 지표 | CloudWatch Metrics | rule execution/error/throttle 계열 지표 |
| Hub/EKS/Pod 지표 | CloudWatch/EKS/kubectl 또는 후속 경량 Prometheus | Kubernetes와 앱 Prometheus metric |
| Lambda 처리 로그 | CloudWatch Logs / Logs Insights | message_id, factory_id, source_type, 오류 원인 추적 |
| Lambda 호출 구간 trace | X-Ray 또는 OpenTelemetry | DynamoDB/S3 호출 시간과 전체 처리 지연 breakdown |

AMP는 2026-05-27 비용 최적화 기준에서 active 구성에서 제거한다. S3 encryption/lifecycle, IoT Rule action, Lambda environment, IAM policy 같은 AWS 리소스 설정 검증은 AWS API, Terraform state, AWS Config 후속 확장으로 확인한다.

### Lambda custom metric 후보

Lambda data processor는 CloudWatch Embedded Metric Format(EMF) 또는 CloudWatch custom metrics로 아래 값을 남긴다.

| Metric | 의미 |
|---|---|
| `MessagesReceived` | Lambda가 받은 전체 메시지 수 |
| `MessagesProcessed` | 정상 처리된 메시지 수 |
| `MessagesSkipped` | schema/validation 오류 등으로 스킵된 메시지 수 |
| `MessagesFailed` | Lambda 처리 실패 수 |
| `ProcessingLatencyMs` | Lambda 내부 전체 처리 시간 |
| `EndToEndLagSeconds` | `processed_at - source_timestamp` 기준 end-to-end 지연 |
| `DynamoDBUpdateLatencyMs` | DynamoDB LATEST/HISTORY#STATE/GRAPH#5M 쓰기 지연 |
| `S3PutLatencyMs` | S3 processed PutObject 지연 |
| `PipelineStatusAgeSeconds` | 최신 infra_state 기준 pipeline age |
| `RiskScore` | factory별 최신 Risk Score |

권장 dimension:

```text
factory_id
source_type
environment_type
status
error_type
```

### Grafana 운영 패널 후보

Grafana는 내부 관리 UI로 유지하고, 필요 시 CloudWatch datasource 또는 후속 경량 Prometheus datasource를 별도 검토한다.

| 패널 | Datasource | 목적 |
|---|---|---|
| factory별 처리량 | CloudWatch | `MessagesProcessed` rate |
| Lambda p95 duration | CloudWatch | Lambda 기본 Duration 또는 `ProcessingLatencyMs` |
| end-to-end lag | CloudWatch | `EndToEndLagSeconds` p50/p95 |
| DynamoDB write latency | CloudWatch | `DynamoDBUpdateLatencyMs` |
| S3 processed write latency | CloudWatch | `S3PutLatencyMs` |
| skipped/failed message count | CloudWatch | schema 오류와 처리 실패 분리 |
| pipeline age | CloudWatch | `PipelineStatusAgeSeconds` |
| Hub/EKS workload 상태 | EKS/CloudWatch/kubectl 또는 후속 경량 Prometheus | Pod/node/service 상태 |

### 구현 우선순위

1. `apps/data-processor/`에 EMF custom metric 로깅 추가
2. Lambda X-Ray tracing 활성화 여부 결정
3. Grafana에 CloudWatch datasource 추가
4. data-pipeline 운영 패널 생성
5. S3 request metrics는 비용을 확인한 뒤 `raw/`, `processed/` 중 필요한 prefix만 활성화
6. 리소스 설정 drift 검증은 AWS Config 또는 정기 AWS API 점검 스크립트로 분리

---

## 관련 파일

| 경로 | 역할 |
|---|---|
| `apps/data-processor/lambda_function.py` | Lambda 핸들러, IoT 처리 분기, freshness refresh 처리 |
| `apps/data-processor/processor/normalizer.py` | 페이로드 정규화 |
| `apps/data-processor/processor/risk.py` | Risk 점수 계산 |
| `apps/data-processor/processor/pipeline_status.py` | Pipeline status 판정 |
| `apps/data-processor/processor/dynamo.py` | DynamoDB 읽기/쓰기 |
| `apps/data-processor/processor/s3_writer.py` | S3 processed 쓰기 |
| `apps/graph-metrics-aggregator/aggregator/handler.py` | GraphAggregator5m Lambda 핸들러 |
| `apps/graph-metrics-aggregator/aggregator/metrics.py` | 5분 그래프 집계 item 생성 |
| `apps/graph-metrics-aggregator/aggregator/dynamo.py` | HISTORY#STATE query, GRAPH#5M put |
| `apps/cloud-infra-collector/` | CloudInfraFast/SlowCollector Lambda |
| `apps/risk-alert-dispatcher/` | S3 processed snapshot alert evaluator, DynamoDB dedupe, Slack sender |
| `infra/data-pipeline/lambda.tf` | DataProcessor Lambda, IAM, CloudWatch, 1분 freshness refresh Scheduler |
| `infra/data-pipeline/graph_aggregator_lambda.tf` | GraphAggregator5m Lambda와 Scheduler |
| `infra/data-pipeline/cloud_infra_fast_collector.tf` | CloudInfraFastCollector Lambda, IAM, Scheduler |
| `infra/data-pipeline/cloud_infra_slow_collector.tf` | CloudInfraSlowCollector Lambda, IAM, EKS access entry, Scheduler |
| `infra/data-pipeline/risk_alert_dispatcher.tf` | RiskAlertDispatcher Lambda, IAM, S3 notification, Slack secret metadata |
| `infra/foundation/dynamodb.tf` | DynamoDB 테이블 리소스 |
| `infra/data-pipeline/iot_rule.tf` | IoT Topic Rule 리소스 |

---

## 2026-05-27 운영 메모

- Factory-A `infra_state` raw payload는 Prometheus 기반 node CPU/memory/disk 사용률을 포함한다.
- Factory-A adapter image는 GitOps에서 `factory-a-log-adapter:main`, `imagePullPolicy: Always`로 배포한다.
- Spoke K3s는 EKS node role을 상속받지 않으므로 `ai-apps/ecr-registry` imagePullSecret을 주기적으로 갱신해야 한다. 만료되면 rollout 시 `403 Forbidden` / `ErrImagePull`이 발생한다.
- `KJW_AEGIS_Data_IoTRule_infra_state_processor`, `KJW_AEGIS_Data_IoTRule_factory_state_processor`는 구형 Lambda가 `processed/` 결과를 덮어써 2026-05-27에 비활성화했다.
- Lambda zip에는 `__pycache__`와 `*.pyc`를 포함하지 않는다. stale bytecode가 들어가면 source 변경과 실제 런타임 동작이 어긋날 수 있다.

## 2026-05-29 운영 메모

- `factory-a`가 2026-05-28T07:54Z 이후 새 메시지를 보내지 않아 DynamoDB LATEST의 기존 `risk.score=100`이 stale 상태로 남는 문제가 있었다.
- 원인은 메시지 수신 시점에만 `pipeline_status`와 `risk`를 갱신하던 구조였다. 데이터가 완전히 끊기면 LATEST를 갱신할 trigger가 없었다.
- `AEGIS-Schedule-DataProcessorRefresh1m`를 배포해 1분마다 DataProcessor Lambda를 `action=refresh_pipeline_status`로 호출하도록 했다.
- 배포 검증 결과 `factory-a`는 `pipeline_status=critical`, `risk.score=0`, `risk.level=danger`로 갱신됐다.
- 같은 시점 `factory-b/c`는 최신 메시지가 계속 들어오므로 refresh 후에도 `pipeline_status=normal`, `risk.score=100`을 유지했다.

## 2026-06-02 운영 메모

- RiskAlertDispatcher를 data-pipeline Terraform root와 build/destroy 생명주기에 포함했다.
- S3 `processed/` ObjectCreated notification은 factory-a/b/c `state_snapshot`과 cloud infra `fast`/`slow` JSON prefix만 Lambda를 호출한다.
- Slack webhook secret metadata는 Terraform이 관리하고, secret value는 `scripts/build/build-data-pipe.sh`가 로컬 `.secrets/` 파일에서 Secrets Manager로 주입한다. URL 값은 repo와 Terraform state에 저장하지 않는다.
- CloudInfraSlowCollector의 EKS Kubernetes API 401 원인은 EKS access entry 누락이었다. `AEGIS-IAMRole-Lambda-CloudInfraSlowCollector`에 `AmazonEKSAdminViewPolicy` cluster scope read access를 적용한 뒤 `errors=[]`, nodes/pods/ArgoCD 정상 수집을 확인했다.
- RiskAlertDispatcher cloud slow rule은 collector error가 있을 때 같은 원인에서 파생된 unknown section 알림을 억제하고 대표 collector error 1건만 전송한다.

## 2026-06-04 운영 메모

- Cloud `fast.factory_freshness`는 대시보드 참고 데이터에 유지되며, 2026-06-04 AWS 배포본 기준 Cloud `overall_status`에도 포함된다.
- RiskAlertDispatcher cloud fast rule은 Lambda error/throttle, DynamoDB throttle, ALB unhealthy host specific alert를 먼저 만든다. 같은 section에 specific alert가 있으면 `data_pipeline_warning` 또는 `backend_runtime_warning` generic alert를 억제한다.
- RiskAlertDispatcher cloud slow rule은 EKS cluster/nodegroup/ASG, nodes, pods, argocd specific alert를 먼저 만든다. EKS specific alert가 있으면 `eks_management_*` generic alert를 억제한다.
- specific으로 설명되지 않는 non-normal section은 generic fallback alert로 유지한다. nodes와 pods처럼 독립적인 specific 문제는 모두 유지한다.
- Cloud warning 연속 관측 정책을 적용했다. `backend_runtime_warning`, `data_pipeline_warning`, `data_pipeline_lambda_errors`는 90초 안에 서로 다른 snapshot 2회 관측 후 전송한다. `eks_management_warning`, `pods_warning`은 450초 안에 서로 다른 snapshot 2회 관측 후 전송한다.
- ALB unhealthy host, Lambda/DynamoDB throttle, collector error, danger/critical은 즉시 알림이다.
- 2026-06-04 실제 AWS Lambda zip 기준 동기화: repo 관리 Lambda 12개를 `aws lambda get-function`으로 다운로드해 로컬 배포 포함 파일과 비교했고, 실행 로직은 로컬과 일치하도록 맞췄다.
- CloudInfraFastCollector/SlowCollector는 같은 zip을 사용하며 AWS `CodeSha256=/FapoibjVCVSbJMI8n/LeJx/0K6UrE3U6MazSzCUezE=` 기준이다. LastModified는 Fast `2026-06-04T07:17:42Z`, Slow `2026-06-04T07:17:06Z`다.
- 2026-06-04 AWS 배포본 기준 CloudInfraFastCollector는 ECS service의 Target Group ARN을 우선하지 않고 `ALB_TARGET_GROUP_NAME`으로 Target Group을 조회한다. Target state는 healthy와 non-healthy 개수로만 나누며 `draining_host_count` 별도 필드는 없다.
- 2026-06-04 AWS 배포본 기준 ALB 조회 실패 fallback이 `status=unknown`이고 `healthy_host_count`가 없으면 `_alb_status()`는 `critical`을 반환한다.
- 2026-06-04 AWS 배포본 기준 Pod phase는 Failed pod가 1개라도 `critical`이다.
- 로컬 검증 결과 `apps/data-processor`, `apps/graph-metrics-aggregator`, `apps/cloud-infra-collector`, `apps/risk-alert-dispatcher` 테스트 80 passed, `apps/daily-report-generator` 테스트 15 passed.
- AWS에는 repo 매핑이 확인되지 않은 `KJW-AEGIS-Data-Lambda-notifier`가 별도 존재한다. 이 함수는 AEGIS repo 관리 Lambda 동기화 범위에서 제외했다.
