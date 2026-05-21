# Data Pipeline 구현 레퍼런스

상태: 구현 기준 source of truth
기준일: 2026-05-21
관련 스펙: `docs/specs/data_storage_pipeline.md`

---

## 개요

Aegis 데이터 파이프라인은 Edge factory에서 발생한 센서·인프라 데이터를 AWS IoT Core로 수신한 뒤 Lambda가 정규화·위험도 계산을 수행하고 DynamoDB와 S3에 이중 저장하는 구조다.

- **실시간 현황 조회** → DynamoDB LATEST
- **그래프·이력 조회** → DynamoDB HISTORY
- **장기 보존·재처리** → S3 processed / raw

---

## 전체 플로우

```
┌──────────────────────────────────────────────────────┐
│                    Edge Devices                      │
│                                                      │
│  [factory-a-log-adapter]  [dummy-data-generator]     │
│            │                       │                 │
│            └──────────┬────────────┘                 │
│                       ▼                              │
│             [edge-iot-publisher]                     │
└───────────────────────┼──────────────────────────────┘
                        │ MQTT
                        │ topic: aegis/{factory_id}/{source_type}
                        ▼
              ┌──────────────────┐
              │  AWS IoT Core    │
              └────────┬─────────┘
                       │
              ┌────────▼──────────────────┐
              │      IoT Topic Rule       │
              │  AEGIS_IoTRule_factory_   │
              │  a/b/c_raw_s3            │
              └────────┬──────────┬───────┘
                       │          │
             S3 Action │          │ Lambda Action
                       │          │
          ┌────────────▼──┐   ┌───▼────────────────────────────┐
          │   S3  raw/    │   │   Lambda: data-processor        │
          │               │   │   AEGIS-Lambda-DataProcessor    │
          │ raw/          │   │   python3.12 · 512MB · 60s      │
          │  {factory_id}/│   └───┬────────────────────────────┘
          │  {source_type}│       │
          │  /yyyy=/mm=/  │       ├──── UpdateItem ────────────────────────┐
          │  dd=/         │       │                                        ▼
          │  {msg_id}.json│       │                          ┌─────────────────────────┐
          └───────────────┘       │                          │   DynamoDB LATEST        │
                                  │                          │   pk: FACTORY#{factory}  │
                                  │                          │   sk: LATEST             │
                                  │                          │   (계속 덮어씀)          │
                                  │                          └─────────────────────────┘
                                  │
                                  ├──── PutItem ─────────────────────────┐
                                  │                                       ▼
                                  │                          ┌─────────────────────────┐
                                  │                          │   DynamoDB HISTORY       │
                                  │                          │   HISTORY#STATE#{ts}     │
                                  │                          │   LATEST snapshot + TTL  │
                                  │                          │   TTL: 48시간            │
                                  │                          └─────────────────────────┘
                                  │
                                  └──── PutObject ───────────────────────┐
                                                                         ▼
                                                          ┌─────────────────────────────┐
                                                          │   S3 processed/              │
                                                          │   {factory_id}/              │
                                                          │     factory_state/...        │
                                                          │     risk_score/...           │
                                                          │     infra_state/...          │
                                                          └─────────────────────────────┘
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
       │  calc_risk()                │  온도(±15) + 습도(±10)
       │                             │  + AI(±10) → score / level
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

```
  Table: AEGIS-DynamoDB-FactoryStatus
  pk = FACTORY#{factory_id}   (factory-a / factory-b / factory-c)

  ┌───────────────────────────────────────────────────────────────────┐
  │ sk = LATEST                                          (TTL 없음)  │
  │                                                                   │
  │   factory_state  →  normalized sensor (온도·습도·기압·AI score)   │
  │   infra_state    →  normalized infra  (nodes·workloads·devices)  │
  │   risk           →  score / level / top_causes                   │
  │   pipeline_status→  status / latest_infra_state_age_seconds      │
  │   last_factory_state_at / last_infra_state_at / updated_at       │
  │                                          ↑ 3초/20초마다 덮어씀   │
  ├───────────────────────────────────────────────────────────────────┤
  │ sk = HISTORY#STATE#2026-05-21T10:00:03.123Z          TTL: 48h   │
  │   LATEST와 같은 구조 + ttl                                      │
  ├───────────────────────────────────────────────────────────────────┤
  │ sk = HISTORY#STATE#2026-05-21T10:00:06.456Z          TTL: 48h   │
  │   factory_state / infra_state / risk / pipeline_status snapshot  │
  ├───────────────────────────────────────────────────────────────────┤
  │   ... (factory_state 또는 infra_state 수신마다 신규 아이템)       │
  └───────────────────────────────────────────────────────────────────┘

  48시간 경과 후 HISTORY 아이템은 DynamoDB TTL에 의해 자동 삭제됨.
  LATEST는 삭제되지 않고 계속 overwrite.
```

---

## S3 버킷 구조

```
  aegis-bucket-data/
  │
  ├── raw/                              ← IoT Rule이 직접 저장 (원본, 가공 없음)
  │   ├── factory-a/
  │   │   ├── factory_state/
  │   │   │   └── yyyy=2026/mm=05/dd=21/
  │   │   │       └── factory-a:factory_state:worker2:2026-05-21T10:00:03Z.json
  │   │   └── infra_state/
  │   │       └── yyyy=2026/mm=05/dd=21/
  │   │           └── factory-a:infra_state:cluster:2026-05-21T10:00:20Z.json
  │   ├── factory-b/  (동일 구조)
  │   └── factory-c/  (동일 구조)
  │
  └── processed/                        ← Lambda가 저장 (정규화·계산 결과)
      ├── factory-a/
      │   ├── factory_state/            ← normalized sensor data
      │   │   └── yyyy=2026/mm=05/dd=21/hh=10/
      │   │       └── {message_id}.json
      │   ├── risk_score/               ← normalized + risk + pipeline_status
      │   │   └── yyyy=2026/mm=05/dd=21/hh=10/
      │   │       └── {message_id}.json
      │   ├── infra_state/             ← normalized infra + pipeline_status
      │   │   └── yyyy=2026/mm=05/dd=21/hh=10/
      │   │       └── {message_id}.json
      │   └── state_snapshot/          ← HISTORY#STATE와 같은 전체 상태, ttl 제외
      │       └── yyyy=2026/mm=05/dd=21/hh=10/
      │           └── {updated_at}.json
      ├── factory-b/  (동일 구조)
      └── factory-c/  (동일 구조)

  raw/      → 90일 후 Glacier Instant Retrieval 전환  (S3 Lifecycle)
  processed/ → 365일 후 Standard-IA 전환             (S3 Lifecycle)
```

---

## Risk 계산 구조

```
  입력: normalize_factory_state() 결과

  ┌─────────────────────────────────────────────────────────────────┐
  │  temperature_celsius                          가중치: 15        │
  │                                                                 │
  │   0°C    32°C            38°C                                   │
  │   ├───────┼───────────────┼────────────────►                   │
  │   │  0점  │  선형 증가    │     15점 고정                       │
  │   │       └──────────────►                                      │
  ├─────────────────────────────────────────────────────────────────┤
  │  humidity_percent                             가중치: 10        │
  │                                                                 │
  │   0%     70%             85%                                    │
  │   ├───────┼───────────────┼────────────────►                   │
  │   │  0점  │  선형 증가    │     10점 고정                       │
  ├─────────────────────────────────────────────────────────────────┤
  │  AI event (fire / fall / bend score)          가중치: 10        │
  │                                                                 │
  │   peak = max(fire_score, fall_score, bend_score)               │
  │   contribution = min(10, peak × 10 + sound_bonus)              │
  │   abnormal_sound 감지 시 sound_bonus = +0.5                    │
  └─────────────────────────────────────────────────────────────────┘

  total_score = temp_contrib + humid_contrib + ai_contrib

  score → level 판정
  ┌──────────┬─────────────┬──────────────┬───────────────┐
  │   0~9    │   10~19     │    20~29     │     ≥ 30      │
  │  normal  │   warning   │    danger    │   critical    │
  └──────────┴─────────────┴──────────────┴───────────────┘
```

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
```

---

## AWS 리소스 목록

| 리소스 | 이름 | 설정 |
|---|---|---|
| Lambda Function | `AEGIS-Lambda-DataProcessor` | python3.12, 512MB, timeout 60s |
| Lambda IAM Role | `AEGIS-IAMRole-Lambda-DataProcessor` | DynamoDB GetItem/PutItem/UpdateItem, S3 PutObject processed/* |
| Lambda IAM Policy | `AEGIS-IAMPolicy-Lambda-DataProcessor` | CloudWatch Logs + DynamoDB + S3 |
| CloudWatch Log Group | `/aws/lambda/AEGIS-Lambda-DataProcessor` | 보존 30일 |
| DynamoDB Table | `AEGIS-DynamoDB-FactoryStatus` | PAY_PER_REQUEST, PITR 활성화 |
| IoT Rule (factory-a) | `AEGIS_IoTRule_factory_a_raw_s3` | S3 + Lambda 액션 |
| IoT Rule (factory-b) | `AEGIS_IoTRule_factory_b_raw_s3` | S3 + Lambda 액션 |
| IoT Rule (factory-c) | `AEGIS_IoTRule_factory_c_raw_s3` | S3 + Lambda 액션 |
| IoT Rule IAM Role | `AEGIS-IAMRole-IoTRule-S3` | S3 raw/factory-a,b,c/* PutObject |

### Lambda 환경 변수

| 변수 | 값 (Terraform 주입) |
|---|---|
| `DYNAMODB_TABLE_NAME` | `AEGIS-DynamoDB-FactoryStatus` |
| `S3_BUCKET_NAME` | `aegis-bucket-data` |
| `HISTORY_TTL_HOURS` | `48` |

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

---

## DynamoDB 키 패턴 요약

| SK | 저장 계기 | 주기 | TTL | 내용 |
|---|---|---|---|---|
| `LATEST` | factory_state / infra_state 수신 | 3초 / 20초 덮어씀 | 없음 | 최신 전체 상태 |
| `HISTORY#STATE#{updated_at}` | factory_state / infra_state 수신 | 3초 / 20초 | 48시간 | LATEST와 같은 구조 + ttl |

> `pk`는 모두 `FACTORY#{factory_id}` 고정.

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
       │                             sk begins_with "HISTORY#STATE#"
       │                             risk 필드 추출
       │
       ├── 환경 데이터 그래프 (온도·습도 등)
       │        └── DynamoDB Query   pk=FACTORY#{id}
       │                             sk begins_with "HISTORY#STATE#"
       │                             factory_state 필드 추출
       │
       ├── 인프라 상태 그래프 (CPU·memory·nodes)
       │        └── DynamoDB Query   pk=FACTORY#{id}
       │                             sk begins_with "HISTORY#STATE#"
       │                             infra_state 필드 추출
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
| DynamoDB HISTORY | 48시간 | TTL 자동 삭제 |
| S3 raw | 90일 후 Glacier IR 전환 | S3 Lifecycle |
| S3 processed | 365일 후 Standard-IA 전환 | S3 Lifecycle |
| CloudWatch Logs | 30일 | Log Group retention |

---

## 관련 파일

| 경로 | 역할 |
|---|---|
| `apps/data-processor/lambda_function.py` | Lambda 핸들러, 처리 분기 |
| `apps/data-processor/processor/normalizer.py` | 페이로드 정규화 |
| `apps/data-processor/processor/risk.py` | Risk 점수 계산 |
| `apps/data-processor/processor/pipeline_status.py` | Pipeline status 판정 |
| `apps/data-processor/processor/dynamo.py` | DynamoDB 읽기/쓰기 |
| `apps/data-processor/processor/s3_writer.py` | S3 processed 쓰기 |
| `infra/foundation/lambda.tf` | Lambda, IAM, CloudWatch 리소스 |
| `infra/foundation/dynamodb.tf` | DynamoDB 테이블 리소스 |
| `infra/foundation/iot_rule.tf` | IoT Topic Rule 리소스 |
