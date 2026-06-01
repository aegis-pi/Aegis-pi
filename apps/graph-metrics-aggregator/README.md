# graph-metrics-aggregator

상태: source of truth
기준일: 2026-06-01

## 목적

DynamoDB `HISTORY#STATE` snapshot을 5분 단위로 집계해 Dashboard 그래프용 read model을 만든다.

입력:

```text
DynamoDB AEGIS-DynamoDB-FactoryStatus
pk = FACTORY#{factory_id}
sk = HISTORY#STATE#{updated_at}
```

출력:

```text
DynamoDB
pk = FACTORY#{factory_id}
sk = GRAPH#5M#{bucket_start}

S3
processed_agg/{factory_id}/metrics_5m/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/mm={MM}.json
```

## 처리 흐름

```text
EventBridge Scheduler (rate 5 minutes)
  -> Lambda AEGIS-Lambda-GraphAggregator5m
      -> query HISTORY#STATE by factory and time bucket
      -> aggregate sensor / risk / AI / infra metrics
      -> put GRAPH#5M DynamoDB item
      -> put processed_agg S3 object
```

## 집계 필드

| 영역 | 필드 |
| --- | --- |
| `sensor` | `temperature_celsius`, `humidity_percent`, `pressure_hpa` |
| `risk` | `score` |
| `ai_detection` | `fire_score`, `fall_score`, `bend_score`, threshold 초과 횟수 |
| `infra` | 하위 호환용 전체 node 평균 `cpu_usage_percent`, `memory_usage_percent`, `disk_usage_percent` |
| `infra.nodes[]` | `node_id`별 `cpu_usage_percent`, `memory_usage_percent`, `disk_usage_percent` 5분 집계 |
| `quality` | source count, expected count, collection rate, empty/partial 여부 |

`infra.nodes[]` 예시:

```json
{
  "node_id": "worker1",
  "role": "worker",
  "cpu_usage_percent": {
    "unit": "percent",
    "count": 14,
    "min": 8.07,
    "max": 11.66,
    "mean": 9.5107,
    "first": 8.4,
    "last": 9.11
  }
}
```

Backend는 노드 그래프를 만들 때 `infra.nodes[].node_id` 기준으로 series를 묶고, chart 기본값은 `mean`을 사용한다. 배포 이전에 생성된 오래된 `GRAPH#5M` item에는 `infra.nodes[]`가 없을 수 있으므로 필요하면 `infra.cpu_usage_percent` 전체 평균으로 fallback한다.

## 환경 변수

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `DYNAMODB_TABLE_NAME` | `AEGIS-DynamoDB-FactoryStatus` | 입력/출력 DynamoDB 테이블 |
| `S3_BUCKET_NAME` | `aegis-bucket-data` | graph aggregate S3 출력 버킷 |
| `FACTORY_IDS` | `factory-a,factory-b,factory-c` | 집계 대상 공장 |
| `BUCKET_MINUTES` | `5` | 집계 bucket 크기 |
| `LOOKBACK_BUCKETS` | `1` | 스케줄 실행 시 닫힌 bucket 몇 개를 처리할지 |
| `GRAPH_TTL_HOURS` | `48` | `GRAPH#5M` DynamoDB TTL |
| `EXPECTED_SAMPLE_INTERVAL_SECONDS` | `3` | quality expected count 계산 기준 |
| `AI_SCORE_THRESHOLD` | `0.7` | AI detection threshold |
| `S3_OUTPUT_PREFIX` | `processed_agg` | S3 출력 prefix |

## 테스트

```bash
cd apps/graph-metrics-aggregator
python3 -m pytest tests/ -v
```

## 관련 문서

- `docs/ops/23_data_pipeline.md`
- `docs/ops/26_dynamodb_key_model.md`
- `infra/data-pipeline/README.md`
