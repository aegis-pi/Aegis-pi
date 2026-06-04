# DynamoDB Key Model

상태: 운영 확인 기준
기준일: 2026-06-04

## 목적

이 문서는 Aegis 데이터 파이프라인이 사용하는 DynamoDB 테이블의 현재 PK/SK 스키마와 실제 아이템 키 패턴을 정리한다.

대상 테이블:

```text
AEGIS-DynamoDB-FactoryStatus
region: ap-south-1
```

## 테이블 키 스키마

실제 AWS `describe-table` 조회 결과와 Terraform 정의가 일치한다.

| 구분 | Attribute | Type | DynamoDB KeyType |
| --- | --- | --- | --- |
| PK | `pk` | `S` | `HASH` |
| SK | `sk` | `S` | `RANGE` |

운영 설정:

| 항목 | 값 |
| --- | --- |
| Billing mode | `PAY_PER_REQUEST` |
| TTL attribute | `ttl` |
| PITR | enabled |
| Stream | `NEW_AND_OLD_IMAGES` |

Terraform source:

- `infra/foundation/dynamodb.tf`
- `infra/foundation/variables.tf`

## 현재 PK 패턴

현재 factory별 파티션을 사용한다.

```text
pk = FACTORY#{factory_id}
```

확인된 PK:

| PK | 의미 |
| --- | --- |
| `FACTORY#factory-a` | Factory A 상태/이력/그래프 |
| `FACTORY#factory-b` | Factory B 상태/이력/그래프 |
| `FACTORY#factory-c` | Factory C 상태/이력/그래프 |
| `CLOUD#infra` | Cloud infra 상태/이력 read model |
| `ALERT#{scope}` | RiskAlertDispatcher cooldown/dedupe 상태 |

## 현재 SK 패턴

| SK 패턴 | 생성 주체 | TTL | 용도 |
| --- | --- | --- | --- |
| `LATEST` | Lambda data processor, DataProcessorRefresh1m | 없음 | factory별 최신 전체 상태 1건 |
| `HISTORY#STATE#{updated_at}` | Lambda data processor, DataProcessorRefresh1m | `HISTORY_TTL_HOURS` | LATEST snapshot 이력 |
| `GRAPH#5M#{bucket_start}` | Graph metrics aggregator | `GRAPH_TTL_HOURS` | 5분 단위 그래프/지표 집계 |
| `HISTORY#FAST#{updated_at}` | CloudInfraFastCollector | 6시간 | Cloud infra 1분 snapshot 이력 |
| `HISTORY#SLOW#{updated_at}` | CloudInfraSlowCollector | 24시간 | Cloud infra 5분 snapshot 이력 |
| `{severity}#{reason}#{status}` | RiskAlertDispatcher | `ALERT_STATE_TTL_SECONDS` | Slack alert cooldown/dedupe |
| `OBSERVATION#{severity}#{reason}#{status}` | RiskAlertDispatcher | `ALERT_STATE_TTL_SECONDS` | 연속 관측이 필요한 Cloud warning 확인 상태 |

### LATEST

```text
pk = FACTORY#{factory_id}
sk = LATEST
```

`factory_state` 또는 `infra_state` 수신 시 같은 아이템을 부분 갱신한다. 2026-05-29 배포된 `AEGIS-Schedule-DataProcessorRefresh1m`도 1분마다 같은 아이템의 `pipeline_status`, `risk`, `updated_at`을 현재 시각 기준으로 갱신한다. 이 refresh는 새 IoT 메시지가 없는 factory의 stale safe/normal 표시를 방지하기 위한 경로다.

주요 필드:

- `factory_state`
- `infra_state`
- `risk`
- `pipeline_status`
- `last_factory_state_at`
- `last_infra_state_at`
- `updated_at`

### HISTORY#STATE

```text
pk = FACTORY#{factory_id}
sk = HISTORY#STATE#{updated_at}
```

`LATEST` 아이템을 복사해 snapshot으로 저장하고 `ttl`을 추가한다. Dashboard의 단기 이력 조회와 graph aggregator 입력으로 사용한다. 일반 IoT 메시지 처리뿐 아니라 DataProcessorRefresh1m 실행도 refresh 결과 snapshot을 남긴다.

### GRAPH#5M

```text
pk = FACTORY#{factory_id}
sk = GRAPH#5M#{bucket_start}
```

`HISTORY#STATE` window를 읽어 5분 단위로 집계한 결과다. Dashboard 그래프 조회와 S3 `processed_agg/` 보조 산출물의 DynamoDB 기준 키로 사용한다.

## CLOUD#infra

Cloud infra metric collector는 factory별 data-plane item과 같은 테이블을 재사용하되, 별도 partition key를 사용한다.

```text
pk = CLOUD#infra
```

### Cloud infra LATEST

```text
pk = CLOUD#infra
sk = LATEST
```

`AEGIS-Lambda-CloudInfraFastCollector`와 `AEGIS-Lambda-CloudInfraSlowCollector`가 같은 item을 부분 갱신한다. 2026-06-04 AWS 배포본 기준 `overall_status`는 `fast.factory_freshness`도 판정에 포함한다.

| Collector | 갱신 필드 | 주기 |
| --- | --- | ---: |
| FastCollector | `fast`, `fast_updated_at`, `overall_status`, `updated_at` | 1분 |
| SlowCollector | `slow`, `slow_updated_at`, `overall_status`, `updated_at` | 5분 |

주요 필드:

- `schema_version = cloud-infra-status-v1`
- `updated_at`
- `fast_updated_at`
- `slow_updated_at`
- `overall_status`
- `fast.backend_runtime`
- `fast.data_pipeline`
- `fast.factory_freshness`
- `slow.eks_management`
- `slow.storage_freshness`

Backend/Dashboard는 CloudWatch, EKS, Kubernetes API, S3를 직접 조회하지 않고 이 item을 기본 read model로 읽는다.

### HISTORY#FAST

```text
pk = CLOUD#infra
sk = HISTORY#FAST#{updated_at}
ttl = now + 6h
```

FastCollector가 `LATEST.fast`를 갱신한 뒤 `LATEST` snapshot을 복사해 저장한다. `snapshot_type=fast`를 포함한다.

### HISTORY#SLOW

```text
pk = CLOUD#infra
sk = HISTORY#SLOW#{updated_at}
ttl = now + 24h
```

SlowCollector가 `LATEST.slow`를 갱신한 뒤 `LATEST` snapshot을 복사해 저장한다. `snapshot_type=slow`를 포함한다.

Cloud infra history item도 테이블 TTL attribute인 `ttl`로 자동 삭제된다. `CLOUD#infra/LATEST`에는 TTL을 두지 않는다.

## ALERT#{scope}

RiskAlertDispatcher는 같은 테이블을 alert state 저장소로 재사용한다.

```text
pk = ALERT#{scope}
sk = {severity}#{reason}#{status}
```

scope 예시:

| Scope | 의미 |
| --- | --- |
| `cloud-infra` | Cloud infra fast/slow alert |
| `factory-a` | Factory A state_snapshot alert |
| `factory-b` | Factory B state_snapshot alert |
| `factory-c` | Factory C state_snapshot alert |

예시:

```text
pk = ALERT#factory-c
sk = danger#nodes_all_not_ready#state_snapshot

pk = ALERT#cloud-infra
sk = warning#kubernetes_api_unauthorized#slow

pk = ALERT#cloud-infra
sk = OBSERVATION#warning#pods_warning#slow
```

주요 필드:

- `scope`
- `source_type`
- `severity`
- `reason`
- `status`
- `last_sent_at`
- `last_observed_at`
- `cooldown_until`
- `last_score`
- `last_source_key`
- `last_source_updated_at`
- `last_slack_status`
- `last_slack_error`
- `ttl`

동일 `pk/sk`는 `cooldown_until` 전까지 Slack 재전송을 skip한다. 또한 `last_source_updated_at`보다 오래된 snapshot은 stale로 보고 skip한다. Alert state item은 TTL 대상이며, `LATEST` read model과 달리 장기 보존 목적이 아니다.

Factory의 비-pipeline 알림은 pipeline 상태 변화와 무관하게 `{severity}#{reason}#state_snapshot` fingerprint를 공유한다. `pipeline_status` 알림은 warning/critical 상태를 fingerprint에 유지한다. 일부 Cloud warning은 cooldown 예약 전에 `OBSERVATION#...` item에서 서로 다른 최신 snapshot의 연속 관측 횟수를 확인한다.

## 실제 조회 샘플

아래는 실제 AWS 테이블에서 확인한 샘플이다. 시간 값은 테이블에 저장된 UTC 문자열이다. Factory 샘플은 2026-05-29 조회 기준이고, Cloud infra/alert 샘플은 2026-06-02 검증 기준이다.

| PK | LATEST | 최신 HISTORY#STATE 샘플 | 최신 GRAPH#5M 샘플 |
| --- | --- | --- | --- |
| `FACTORY#factory-a` | `updated_at=2026-05-29T06:48:45.209Z`, `pipeline_status=critical`, `risk.score=0` | `HISTORY#STATE#2026-05-29T06:48:45.209Z` | `GRAPH#5M#2026-05-29T00:10:00Z` |
| `FACTORY#factory-b` | `updated_at=2026-05-29T06:49:02.806Z`, `pipeline_status=normal`, `risk.score=100` | `HISTORY#STATE#2026-05-29T06:49:02.806Z` | `GRAPH#5M#2026-05-29T00:10:00Z` |
| `FACTORY#factory-c` | `updated_at=2026-05-29T06:49:01.949Z`, `pipeline_status=normal`, `risk.score=100` | `HISTORY#STATE#2026-05-29T06:49:01.949Z` | `GRAPH#5M#2026-05-29T00:10:00Z` |

Cloud infra sample:

| PK | LATEST | 최신 fast history | 최신 slow history |
| --- | --- | --- | --- |
| `CLOUD#infra` | `overall_status=normal`, `fast.errors=[]`, `slow.errors=[]` | `HISTORY#FAST#{updated_at}` | `HISTORY#SLOW#{updated_at}` |

Alert sample:

| PK | SK 예시 | 의미 |
| --- | --- | --- |
| `ALERT#cloud-infra` | `warning#kubernetes_api_unauthorized#slow` | Cloud slow Kubernetes API unauthorized alert dedupe |
| `ALERT#factory-c` | `danger#nodes_all_not_ready#state_snapshot` | Factory C danger cause alert dedupe |
| `ALERT#cloud-infra` | `OBSERVATION#warning#pods_warning#slow` | Cloud slow warning 연속 관측 확인 |

공장별 Query count 샘플:

| PK | Count |
| --- | ---: |
| `FACTORY#factory-a` | 34517 |
| `FACTORY#factory-b` | 78745 |
| `FACTORY#factory-c` | 78724 |

## 조회 패턴

현재 상태 조회:

```text
GetItem
pk = FACTORY#{factory_id}
sk = LATEST
```

Cloud infra 현재 상태 조회:

```text
GetItem
pk = CLOUD#infra
sk = LATEST
```

상태 이력 조회:

```text
Query
pk = FACTORY#{factory_id}
sk begins_with HISTORY#STATE#
```

5분 그래프 조회:

```text
Query
pk = FACTORY#{factory_id}
sk begins_with GRAPH#5M#
```

Cloud infra 최근 이력 조회:

```text
Query
pk = CLOUD#infra
sk begins_with HISTORY#FAST#

Query
pk = CLOUD#infra
sk begins_with HISTORY#SLOW#
```

Alert dedupe item 조회:

```text
GetItem
pk = ALERT#{scope}
sk = {severity}#{reason}#{status}
```

특정 시간 범위 조회는 SK가 ISO-8601 UTC 문자열을 포함하므로 `between` 조건을 사용한다.

## 관련 코드

| 파일 | 역할 |
| --- | --- |
| `infra/foundation/dynamodb.tf` | DynamoDB 테이블 생성 |
| `infra/data-pipeline/dynamodb.tf` | foundation 테이블 data source 참조 |
| `apps/data-processor/processor/dynamo.py` | `LATEST`, `HISTORY#STATE` 읽기/쓰기 |
| `apps/graph-metrics-aggregator/aggregator/dynamo.py` | `HISTORY#STATE` query, graph item put |
| `apps/graph-metrics-aggregator/aggregator/metrics.py` | `GRAPH#5M` item 생성 |
| `apps/cloud-infra-collector/cloud_infra/dynamo.py` | `CLOUD#infra/LATEST`, `HISTORY#FAST`, `HISTORY#SLOW` 읽기/쓰기 |
| `apps/risk-alert-dispatcher/alert_dispatcher/dedupe.py` | `ALERT#{scope}` cooldown/dedupe item update |
| `infra/data-pipeline/cloud_infra_fast_collector.tf` | Fast collector Lambda/Scheduler/IAM |
| `infra/data-pipeline/cloud_infra_slow_collector.tf` | Slow collector Lambda/Scheduler/IAM/EKS access entry |
| `infra/data-pipeline/risk_alert_dispatcher.tf` | RiskAlertDispatcher Lambda/S3 trigger/IAM/secret metadata |
| `docs/ops/23_data_pipeline.md` | 전체 데이터 파이프라인 운영 기준 |
| `docs/ops/31_risk_alert_dispatcher.md` | alert pipeline 운영 기준 |

## 주의 사항

- 테이블에는 GSI가 없다. 현재 조회는 `pk`와 `sk` range 조건에 의존한다.
- `LATEST`는 TTL이 없어 계속 유지된다.
- `HISTORY#STATE`, `GRAPH#5M`, `HISTORY#FAST`, `HISTORY#SLOW`, `ALERT#` item은 TTL 대상이다. 보존 시간은 item의 `ttl` 값으로 결정된다.
- Dashboard/API가 전체 공장 목록을 직접 조회해야 한다면 현재 구조에서는 factory id 목록을 별도 설정으로 갖거나, 제한적인 scan 또는 별도 registry item을 추가해야 한다.
- Cloud infra dashboard/API는 `CLOUD#infra/LATEST`를 읽고, AWS service API를 직접 반복 조회하지 않는다.
