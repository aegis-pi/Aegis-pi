# LLM Daily Factory Report Plan

상태: source of truth
기준일: 2026-05-28
범위: MVP 포함 기능

## 목적

이 문서는 Aegis-Pi MVP에 포함할 Bedrock 기반 factory별 일일 운영 보고서 생성 기능의 기준 설계다.

앞으로 LLM 기반 보고서 생성과 관련된 구현, 문서 갱신, 이슈 분해는 이 문서를 source of truth로 삼는다. 사용자가 이 기능의 범위나 동작 방식을 바꾸면 이 문서를 먼저 갱신한 뒤 구현 문서와 코드를 맞춘다.

## 결정 요약

- LLM 기반 보고서는 MVP 범위에 포함한다.
- 보고서는 전체 공장 통합 보고서가 아니라 factory별 개별 일일 보고서로 생성한다.
- 보고서 생성 기준 데이터는 S3 `processed/` 데이터를 우선 사용한다.
- Bedrock은 원본 데이터를 직접 분석하지 않는다.
- Lambda가 단순 평균 집계가 아니라 통계, 극값, percentile, threshold 초과 구간, spike, 이상 이벤트, 권장 확인 항목 후보 생성을 수행한다.
- hour 경계에 걸친 이벤트는 daily merge 단계에서 병합한다.
- 주요 이벤트는 severity score로 우선순위를 정하고, report-context에는 상위 이벤트만 전달한다.
- factory별 데이터 성격(`physical-rpi`, `vm-mac`, `vm-windows`, dummy/testbed 여부)을 context에 포함해 해석을 분리한다.
- Bedrock은 구조화된 `report-context.json`을 읽고 운영자가 읽기 쉬운 Markdown 초안을 작성한다.
- LLM 출력은 운영 판단의 정본이 아니라 검토용 초안이다.
- 보고서와 함께 Bedrock 입력 근거인 `report-context.json`을 S3에 저장한다.
- 기본 산출물은 Markdown이며, DOCX/PDF 산출물은 확장 범위로 포함한다.
- Bedrock은 DOCX/PDF 바이너리를 직접 생성하지 않고, 텍스트 또는 구조화 JSON만 생성한다.
- DOCX/PDF 파일 생성은 별도 후처리 Lambda가 템플릿과 Bedrock 출력 텍스트를 조합해 수행한다.
- Bedrock 출력 후 핵심 수치, 날짜, factory ID가 context와 일치하는지 검증한다.
- S3 `raw/`는 MVP 보고서 생성 입력에서 제외한다. 원본 감사와 재처리 용도는 유지한다.

## 참조 문서

작업 시작 전 아래 문서를 함께 확인한다.

| 문서 | 참조 이유 |
| --- | --- |
| `docs/product/00_mvp_scope.md` | LLM 보고서를 MVP 범위로 재분류해야 하는 제품 범위 문서 |
| `docs/product/02_requirements_definition.md` | LLM 보고서 요구사항과 NFR/COST 항목 반영 대상 |
| `docs/planning/00_project_overview.md` | 프로젝트 전체 방향과 보고서 자동화 위치 |
| `docs/planning/03_evaluation_plan.md` | 보고서가 사용할 운영 지표와 평가 기준 |
| `docs/planning/07_dashboard_vpc_extension_plan.md` | Dashboard/Data VPC와 조회 데이터 경계 |
| `docs/planning/11_delivery_ownership_flow.md` | Terraform, Lambda, GitHub Actions, ArgoCD 책임 경계 |
| `docs/planning/16_m4_edge_data_plane_implementation.md` | Edge data-plane 구현과 검증 이력 |
| `docs/specs/iot_data_format.md` | `factory_state`, `infra_state` canonical JSON 계약 |
| `docs/specs/data_storage_pipeline.md` | S3 raw/processed, DynamoDB LATEST/HISTORY#STATE 저장 계약 |
| `docs/ops/23_data_pipeline.md` | IoT Core -> Lambda -> DynamoDB/S3 processed 구현 레퍼런스 |
| `apps/data-processor/README.md` | 기존 Lambda data processor 구조와 저장 경로 |
| `infra/data-pipeline/README.md` | data-pipeline Terraform 레이어와 build/destroy 기준 |
| `docs/report/README.md` | 결과 보고서 문서 위치와 보고 원칙 |

## 보고서의 역할

보고서는 전날 factory별 운영 상태를 사람이 빠르게 검토할 수 있도록 요약하는 초안이다.

보고서가 제공해야 하는 판단은 아래에 한정한다.

- 전날 해당 factory의 전체 상태가 정상/주의/위험 중 어디에 가까웠는지
- Risk Score가 언제, 얼마나 나빠졌는지
- 센서/AI 값 중 확인할 만한 이상 징후가 있었는지
- 노드, 워크로드, 장치 상태에 운영상 확인할 이벤트가 있었는지
- 데이터 파이프라인 수집률과 공백이 운영 신뢰도에 영향을 줄 수준이었는지
- 다음 작업자가 확인해야 할 항목은 무엇인지
- 보고서가 근거로 삼은 데이터의 한계는 무엇인지

보고서가 하지 않는 일은 아래와 같다.

- 장애 원인 확정
- 운영 조치 자동 실행
- 모델 재학습 자동 결정
- 배포 변경 자동 결정
- 법적/감사용 최종 보고서 생성
- S3 raw 원본 전체에 대한 LLM 직접 분석

## 보고서 수신자

MVP 보고서의 1차 수신자는 운영자다. 단, 프로젝트 평가나 데모에서도 읽을 수 있도록 운영 근거와 한계를 명확히 적는다.

보고서 톤은 아래 기준을 따른다.

- 한국어
- 운영 리포트 형식
- 추정 표현은 명확히 표시
- JSON 근거에 없는 사실은 작성하지 않음
- 수치, 시간, factory ID는 입력 context 값을 그대로 사용
- LLM 초안이며 운영자 검토가 필요하다는 한계를 포함

## 생성 주기와 기준 시간

MVP 기준은 아래와 같다.

| 항목 | 값 |
| --- | --- |
| 생성 주기 | 하루 1회 |
| 실행 시각 | 매일 00:30 KST 권장 |
| 대상 기간 | 전일 00:00:00~23:59:59 KST |
| late arrival 대기 | 30분 |
| 대상 factory | `factory-a`, `factory-b`, `factory-c` |
| 출력 단위 | factory별 보고서 1개 |
| 출력 형식 | Markdown + context JSON |
| 확장 출력 형식 | DOCX/PDF |

예시:

```text
2026-01-02 00:30 KST 실행
대상 기간: 2026-01-01 00:00:00~23:59:59 KST
출력:
- factory-a 2026-01-01 일일 보고서
- factory-b 2026-01-01 일일 보고서
- factory-c 2026-01-01 일일 보고서
```

주의:

S3 processed partition이 UTC 기준 timestamp에서 생성될 수 있으므로, 구현 시 KST report window와 S3 prefix 조회 범위를 분리해서 계산한다. KST 하루가 UTC 날짜 두 개에 걸칠 수 있으면 해당 UTC prefix를 모두 조회한 뒤 `source_timestamp` 또는 `processed_at` 기준으로 필터링한다.

## 전체 파이프라인

MVP 확정 생성 방식은 `Factory x Hour Map` 구조다.

목표는 S3 `processed/`에 저장된 하루치 small object를 Lambda 하나가 모두 읽지 않고, factory와 hour 단위로 잘게 나눠 안정적으로 처리하는 것이다. Bedrock은 원본 데이터를 직접 읽지 않고, Lambda가 만든 `report-context.json`만 입력으로 받는다.

```text
EventBridge Scheduler
  -> Step Functions: DailyFactoryReportStateMachine
      -> PrepareReportWindow Lambda
      -> Map factories
          -> Map hours
              -> AggregateFactoryHour Lambda
          -> MergeFactoryDaily Lambda
          -> GenerateFactoryReport Lambda
```

Lambda 함수는 factory별로 따로 만들지 않는다. 역할별 공통 Lambda가 `factory_id`, `report_date`, `hour` 입력을 받아 여러 번 실행된다.

```text
Lambda 함수 개수: 4개
factory별 함수 개수: 만들지 않음
factory별 분리 방식: 입력 파라미터와 S3 prefix로 분리
hour별 분리 방식: Step Functions Map state로 분리
```

역할별 Lambda:

| Lambda | 실행 횟수/day | 책임 |
| --- | ---: | --- |
| `PrepareReportWindow` | 1 | report date, KST window, S3 조회 범위, factory/hour 목록, output prefix 계산 |
| `AggregateFactoryHour` | 72 | factory 1개 + hour 1개의 S3 processed 데이터를 읽어 signal/event summary 생성 |
| `MergeFactoryDaily` | 3 | factory별 24개 hourly summary를 daily summary와 Bedrock context로 병합 |
| `GenerateFactoryReport` | 3 | `report-context.json`을 읽어 Bedrock 호출, 출력 검증, report 저장 |

MVP에서 별도 Lambda로 나누지 않는 역할:

| 역할 | 처리 위치 | 이유 |
| --- | --- | --- |
| report context build | `MergeFactoryDaily` | daily summary 생성 직후 같은 입력을 사용하므로 분리 이점이 작음 |
| Bedrock output validation | `GenerateFactoryReport` | Bedrock 출력 직후 context와 대조 가능 |
| Markdown render/save | `GenerateFactoryReport` | Markdown은 텍스트 출력이므로 별도 렌더링 Lambda가 필요 없음 |
| DOCX/PDF render | 확장 범위 | Lambda Layer 또는 container image 선택이 필요하므로 MVP 기본 경로에서 분리 |

## 생성 순서 상세

이 섹션만 보고도 구현을 시작할 수 있도록, 2026-01-02 00:30 KST에 2026-01-01 보고서를 만드는 흐름을 기준으로 작성한다.

### 1. 전일 데이터 적재

1월 1일 동안 기존 data-plane이 계속 동작한다.

```text
factory-a/b/c
  -> edge-iot-publisher
  -> AWS IoT Core
      -> S3 raw
      -> Lambda data processor
          -> DynamoDB LATEST/HISTORY#STATE
          -> S3 processed
```

보고서 파이프라인은 S3 `processed/`를 읽는다. S3 `raw/`는 MVP 보고서 생성 입력에서 제외한다.

기본 입력 dataset:

```text
processed/{factory_id}/factory_state/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/
processed/{factory_id}/risk_score/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/
processed/{factory_id}/infra_state/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/
```

보조 입력 dataset:

```text
processed/{factory_id}/state_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/
```

`state_snapshot/`은 MVP 기본 입력이 아니다. `factory_state/`, `risk_score/`, `infra_state/`만으로 보고서에 필요한 필드가 부족할 때만 제한적으로 사용한다.

입력 규모 기준:

```text
factory_state: 3초 주기 = 28,800 objects/factory/day
risk_score: 3초 주기 = 28,800 objects/factory/day
infra_state: 20초 주기 = 4,320 objects/factory/day

기본 입력 합계:
61,920 objects/factory/day
185,760 objects/day for 3 factories
```

### 2. EventBridge Scheduler 실행

매일 00:30 KST에 EventBridge Scheduler가 Step Functions state machine을 시작한다.

권장 schedule:

```text
cron(30 15 * * ? *)  # UTC 기준. KST 00:30
```

초기 입력 예시:

```json
{
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "factories": ["factory-a", "factory-b", "factory-c"],
  "report_type": "daily_factory_operations_draft"
}
```

`report_date`가 입력에 없으면 `PrepareReportWindow`가 실행 시각 기준 전일 KST 날짜를 계산한다.

### 3. PrepareReportWindow Lambda

`PrepareReportWindow`는 보고서 생성 전체의 공통 실행 계획을 만든다.

입력:

```json
{
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "factories": ["factory-a", "factory-b", "factory-c"],
  "report_type": "daily_factory_operations_draft"
}
```

필수 처리:

1. `report_date`를 확정한다.
2. KST 기준 report window를 계산한다.
3. KST report window에 대응되는 UTC timestamp 범위를 계산한다.
4. S3 partition 후보를 계산한다.
5. factory 목록을 확정한다.
6. `hour_items` 목록 `00`~`23`을 만든다. 각 item은 `hour`와 `hour_window`를 포함한다.
7. output prefix를 만든다.
8. Step Functions Map이 바로 사용할 수 있는 factory item 배열을 만든다.

주의:

S3 processed key는 `source_timestamp`의 UTC 시각 기준으로 `yyyy/mm/dd/hh` partition을 만들 수 있다. KST 하루는 UTC 날짜 두 개에 걸칠 수 있으므로, 구현은 KST hour를 그대로 S3 prefix로 단정하지 않는다.

권장 출력:

```json
{
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "window": {
    "start_kst": "2026-01-01T00:00:00+09:00",
    "end_kst": "2026-01-01T23:59:59+09:00",
    "start_utc": "2025-12-31T15:00:00Z",
    "end_utc": "2026-01-01T14:59:59Z"
  },
  "hour_items": [
    {
      "hour": "00",
      "hour_window": {
        "start_kst": "2026-01-01T00:00:00+09:00",
        "end_kst": "2026-01-01T00:59:59+09:00",
        "start_utc": "2025-12-31T15:00:00Z",
        "end_utc": "2025-12-31T15:59:59Z"
      }
    },
    {
      "hour": "01",
      "hour_window": {
        "start_kst": "2026-01-01T01:00:00+09:00",
        "end_kst": "2026-01-01T01:59:59+09:00",
        "start_utc": "2025-12-31T16:00:00Z",
        "end_utc": "2025-12-31T16:59:59Z"
      }
    },
    {
      "hour": "23",
      "hour_window": {
        "start_kst": "2026-01-01T23:00:00+09:00",
        "end_kst": "2026-01-01T23:59:59+09:00",
        "start_utc": "2026-01-01T14:00:00Z",
        "end_utc": "2026-01-01T14:59:59Z"
      }
    }
  ],
  "datasets": ["factory_state", "risk_score", "infra_state"],
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01",
  "factory_items": [
    {
      "factory_id": "factory-a",
      "report_date": "2026-01-01",
      "timezone": "Asia/Seoul",
      "window": {
        "start_kst": "2026-01-01T00:00:00+09:00",
        "end_kst": "2026-01-01T23:59:59+09:00",
        "start_utc": "2025-12-31T15:00:00Z",
        "end_utc": "2026-01-01T14:59:59Z"
      },
      "hour_items": "<same 24 hour_items as top-level>",
      "datasets": ["factory_state", "risk_score", "infra_state"],
      "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
    }
  ]
}
```

### 4. Factory Map

Step Functions `Map` state가 `factory_items`를 순회한다.

```text
factory-a branch
factory-b branch
factory-c branch
```

요구사항:

- factory branch는 서로 독립적이어야 한다.
- 한 factory 실패가 다른 factory 보고서 생성을 막지 않아야 한다.
- branch별 결과는 `success`, `insufficient_data`, `failed` 중 하나로 반환한다.
- `factory-a`는 실제 센서/physical-rpi로 해석한다.
- `factory-b`, `factory-c`는 dummy/testbed로 해석한다.

Factory Map item 예시:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "hour_items": [
    {
      "hour": "00",
      "hour_window": {
        "start_kst": "2026-01-01T00:00:00+09:00",
        "end_kst": "2026-01-01T00:59:59+09:00",
        "start_utc": "2025-12-31T15:00:00Z",
        "end_utc": "2025-12-31T15:59:59Z"
      }
    }
  ],
  "datasets": ["factory_state", "risk_score", "infra_state"],
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
}
```

### 5. Hour Map

Factory branch 내부에서 `hour_items`를 순회한다.

```text
factory-a hh=00
factory-a hh=01
...
factory-a hh=23
```

각 item은 `AggregateFactoryHour` Lambda 입력으로 변환된다.

입력 예시:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "hour": "15",
  "hour_window": {
    "start_kst": "2026-01-01T15:00:00+09:00",
    "end_kst": "2026-01-01T15:59:59+09:00"
  },
  "datasets": ["factory_state", "risk_score", "infra_state"],
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
}
```

권장 concurrency:

```text
Factory Map max concurrency: 3
Hour Map max concurrency: 6~12
```

동시성을 너무 높이면 S3 GET, Lambda concurrency, CloudWatch log burst가 커질 수 있다. MVP는 안정성을 우선해 낮은 concurrency에서 시작한다.

### 6. AggregateFactoryHour Lambda

`AggregateFactoryHour`는 특정 factory의 특정 1시간 데이터를 처리한다.

이 Lambda의 목적은 평균 1개를 만드는 것이 아니다. 원본 수천 건을 보고서에 넣기 좋은 signal/event 형태로 줄이되, spike, worst period, threshold 초과 구간, evidence를 보존하는 것이다.

입력 dataset별 예상 object 수:

```text
factory_state: 약 1,200 objects/hour
risk_score: 약 1,200 objects/hour
infra_state: 약 180 objects/hour
합계: 약 2,580 objects/factory/hour
```

필수 처리 순서:

1. 입력 파라미터 검증
2. KST hour window를 UTC range로 변환
3. dataset별 S3 prefix 후보 계산
4. S3 `ListObjectsV2` 실행
5. object key 목록을 dataset별로 수집
6. S3 object를 bounded concurrency로 읽음
7. JSON parse 실패, schema 누락, timestamp 누락 record를 `invalid_record_count`로 기록
8. `source_timestamp` 또는 `processed_at` 기준으로 hour window 밖 record 제거
9. `message_id` 기준 duplicate 제거
10. timestamp 기준 정렬
11. dataset별 reducer로 통계/이벤트 계산
12. evidence message id 또는 S3 key 보존
13. hourly summary JSON 저장
14. Lambda 결과로 summary S3 key 반환

S3 read 기준:

- 모든 object를 메모리에 배열로 쌓지 않는다.
- record를 읽는 즉시 reducer에 반영한다.
- concurrency는 환경변수로 조절한다.
- 권장 기본값은 `S3_GET_CONCURRENCY=16`이다.
- object별 성공 로그를 남기지 않는다.

필수 산출 지표:

| 영역 | 필수 값 |
| --- | --- |
| input | actual count, expected count, invalid count, duplicate count |
| data quality | collection rate, max gap seconds, gap windows |
| risk | avg, min, max, p05, p95, warning/danger duration, worst periods |
| sensor | temperature/humidity/pressure avg, min, max, p05, p95, threshold duration |
| AI | max fire/fall/bend score, p95 score, threshold duration, abnormal sound count |
| infra | node not ready count/minutes, workload restart delta, unhealthy workload minutes |
| pipeline | warning/critical minutes, max pipeline gap |
| event | spike events, threshold windows, risk degradation windows, evidence ids |

출력 저장 위치:

```text
s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=01/dd=01/factory-a/intermediate/hourly/hh=15.json
```

Lambda 반환 예시:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "hour": "15",
  "status": "success",
  "summary_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/intermediate/hourly/hh=15.json",
  "input_counts": {
    "factory_state": 1194,
    "risk_score": 1194,
    "infra_state": 178
  },
  "event_count": 2
}
```

Hourly summary schema 예시:

```json
{
  "schema_version": "0.1.0",
  "summary_type": "factory_hour",
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "hour": "15",
  "hour_window": {
    "start_kst": "2026-01-01T15:00:00+09:00",
    "end_kst": "2026-01-01T15:59:59+09:00"
  },
  "input_counts": {
    "factory_state": 1194,
    "risk_score": 1194,
    "infra_state": 178,
    "invalid_records": 0,
    "duplicate_records": 1
  },
  "expected_counts": {
    "factory_state": 1200,
    "risk_score": 1200,
    "infra_state": 180
  },
  "data_quality": {
    "factory_state_collection_rate": 0.995,
    "risk_score_collection_rate": 0.995,
    "infra_state_collection_rate": 0.989,
    "data_gap_count": 1,
    "max_gap_seconds": 18,
    "gap_windows": [
      {
        "dataset": "infra_state",
        "time_range": "15:20:00~15:20:18",
        "duration_seconds": 18
      }
    ]
  },
  "risk": {
    "avg_score": 84.2,
    "min_score": 51.2,
    "max_score": 98.7,
    "p05_score": 61.5,
    "p95_score": 97.1,
    "warning_minutes": 15,
    "danger_minutes": 0,
    "top_causes": ["temperature", "fall_score"],
    "worst_periods": [
      {
        "time_range": "15:10~15:12",
        "min_score": 51.2,
        "level": "warning",
        "top_causes": ["temperature", "fall_score"],
        "evidence_message_ids": [
          "factory-a:factory_state:worker2:2026-01-01T06:10:03Z"
        ]
      }
    ]
  },
  "factory_state": {
    "temperature_avg": 29.1,
    "temperature_max": 42.8,
    "temperature_p95": 38.6,
    "temperature_over_threshold_minutes": 12,
    "humidity_avg": 62.4,
    "humidity_max": 71.0,
    "pressure_min": 1007.1,
    "pressure_max": 1014.5,
    "max_fire_score": 0.1,
    "max_fall_score": 0.91,
    "fall_score_p95": 0.42,
    "fall_score_over_threshold_seconds": 120,
    "max_bend_score": 0.33,
    "abnormal_sound_count": 0,
    "spike_events": [
      {
        "type": "fall_score_spike",
        "time_range": "15:10~15:12",
        "max_score": 0.91,
        "duration_seconds": 120
      }
    ]
  },
  "infra": {
    "infra_state_count": 178,
    "node_not_ready_count": 0,
    "node_not_ready_minutes": 0,
    "workload_restart_total": 1,
    "unhealthy_workload_minutes": 0
  },
  "pipeline": {
    "pipeline_warning_minutes": 0,
    "pipeline_critical_minutes": 0,
    "max_gap_seconds": 18
  },
  "events": [
    {
      "time_range": "15:10~15:25",
      "severity": "warning",
      "severity_score": 54.8,
      "type": "risk_degradation",
      "summary": "Risk Score dropped below warning threshold",
      "evidence": {
        "min_score": 51.2,
        "temperature_max": 42.8,
        "max_fall_score": 0.91,
        "evidence_message_ids": [
          "factory-a:factory_state:worker2:2026-01-01T06:10:03Z"
        ]
      }
    }
  ]
}
```

빈 hour 처리:

- 해당 hour에 데이터가 전혀 없으면 Lambda는 실패하지 않는다.
- `status="empty"` summary를 저장한다.
- `MergeFactoryDaily`가 data quality 문제로 반영한다.

### 7. MergeFactoryDaily Lambda

`MergeFactoryDaily`는 factory별 24개 hourly summary를 읽어 daily summary와 Bedrock context를 만든다.

입력:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "hour_results": [
    {
      "hour": "00",
      "status": "success",
      "summary_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/intermediate/hourly/hh=00.json"
    },
    {
      "hour": "01",
      "status": "success",
      "summary_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/intermediate/hourly/hh=01.json"
    }
  ],
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
}
```

`MergeFactoryDaily`는 `hour_results[*].summary_key`를 읽어 hourly summary를 가져온다.

필수 처리 순서:

1. 24개 hourly result와 summary 존재 여부 확인
2. 누락된 hour는 `missing_hour`로 표시
3. hourly summary를 hour 순서로 정렬
4. count, duration, collection rate 병합
5. daily min/max/p05/p95 계산
6. warning/danger duration 합산
7. hour 경계 이벤트 병합
8. severity score 재계산
9. daily top event N개 선정
10. factory interpretation mode 추가
11. data limitation 작성
12. `factory-daily-summary.json` 저장
13. `report-context.json` 저장
14. Lambda 결과로 context S3 key 반환

출력 저장 위치:

```text
reports/daily/yyyy=2026/mm=01/dd=01/factory-a/factory-daily-summary.json
reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json
```

`factory-daily-summary.json`은 내부 집계 결과다. `report-context.json`은 Bedrock 입력이다.

Daily summary 예시:

```json
{
  "schema_version": "0.1.0",
  "summary_type": "factory_daily",
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "factory_profile": {
    "environment_type": "physical-rpi",
    "input_module_type": "sensor",
    "interpretation_mode": "production_edge"
  },
  "data_quality": {
    "factory_state_expected_count": 28800,
    "factory_state_actual_count": 28760,
    "risk_score_expected_count": 28800,
    "risk_score_actual_count": 28760,
    "infra_state_expected_count": 4320,
    "infra_state_actual_count": 4298,
    "factory_state_collection_rate": 0.9986,
    "infra_state_collection_rate": 0.9949,
    "missing_hour_count": 0,
    "data_gap_count": 2,
    "max_gap_minutes": 7,
    "duplicate_message_count": 0,
    "invalid_record_count": 0
  },
  "risk": {
    "avg_score": 87.1,
    "min_score": 51.2,
    "max_score": 99.0,
    "dominant_level": "normal",
    "worst_level": "warning",
    "warning_minutes": 35,
    "danger_minutes": 0,
    "top_causes": ["temperature", "fall_score"],
    "worst_periods": [
      {
        "time_range": "15:10~15:25",
        "min_score": 51.2,
        "top_causes": ["temperature", "fall_score"]
      }
    ]
  },
  "factory_state": {
    "temperature_avg": 27.4,
    "temperature_max": 42.8,
    "temperature_p95": 38.6,
    "temperature_over_threshold_minutes": 12,
    "humidity_avg": 61.2,
    "humidity_max": 72.5,
    "max_fire_score": 0.1,
    "max_fall_score": 0.91,
    "fall_score_p95": 0.42,
    "fall_score_over_threshold_seconds": 120,
    "max_bend_score": 0.33,
    "abnormal_sound_count": 0
  },
  "infra": {
    "node_not_ready_count": 1,
    "node_not_ready_minutes": 3,
    "workload_restart_total": 4,
    "unhealthy_workload_minutes": 0
  },
  "pipeline": {
    "pipeline_warning_minutes": 9,
    "pipeline_critical_minutes": 0,
    "critical_gap_count": 0
  },
  "events": [
    {
      "time_range": "15:10~15:25",
      "severity": "warning",
      "severity_score": 54.8,
      "type": "risk_degradation",
      "summary": "Risk Score dropped to 51.2",
      "evidence": {
        "temperature_max": 42.8,
        "max_fall_score": 0.91,
        "evidence_message_ids": [
          "factory-a:factory_state:worker2:2026-01-01T06:10:03Z"
        ]
      }
    }
  ],
  "data_limitations": [
    "Report is based on S3 processed data, not S3 raw payloads.",
    "LLM output is an operational draft and requires operator review."
  ]
}
```

`report-context.json`은 Bedrock prompt에 넣을 compact context다. 원칙은 아래와 같다.

- daily summary 전체를 그대로 넣되, hourly details는 필요한 것만 넣는다.
- hour별 full event list를 모두 넣지 않고 severity 상위 이벤트 중심으로 제한한다.
- raw payload 전체를 넣지 않는다.
- secret, token, certificate, private key를 포함하지 않는다.

### 8. GenerateFactoryReport Lambda

`GenerateFactoryReport`는 `report-context.json`을 읽고 Bedrock으로 보고서 초안을 생성한다.

입력:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json",
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
}
```

필수 처리 순서:

1. `report-context.json` 읽기
2. context schema validation
3. prompt 생성
4. Bedrock 호출
5. Bedrock 출력 JSON 또는 Markdown 수신
6. 핵심 invariant 검증
7. Markdown report 저장
8. generation metadata 저장
9. Lambda 결과 반환

Bedrock prompt 원칙:

- 한국어 운영 보고서 형식으로 작성한다.
- 입력 context에 없는 사실을 만들지 말라고 명시한다.
- 수치, 날짜, factory ID는 context 값을 그대로 사용하라고 명시한다.
- 추정은 추정이라고 표시하게 한다.
- 운영자 검토가 필요한 초안임을 포함하게 한다.
- JSON key와 evidence 값을 임의 변경하지 않게 한다.

검증해야 하는 invariant:

| 항목 | 검증 방식 |
| --- | --- |
| `factory_id` | report에 context factory_id가 포함되어야 함 |
| `report_date` | report에 context report_date가 포함되어야 함 |
| 핵심 수치 | min risk, warning minutes, collection rate 등 주요 수치가 context와 일치해야 함 |
| 금지 내용 | raw secret/token/private key 패턴이 없어야 함 |
| hallucination 방지 | context에 없는 factory 이름이나 날짜가 없어야 함 |

출력 저장 위치:

```text
reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report.md
reports/daily/yyyy=2026/mm=01/dd=01/factory-a/generation-metadata.json
```

`generation-metadata.json` 예시:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
  "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json",
  "report_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report.md",
  "validation_status": "passed",
  "input_token_count": 12000,
  "output_token_count": 2200,
  "created_at": "2026-01-02T00:31:30+09:00"
}
```

### 9. Step Functions 최종 결과

State machine은 factory별 결과를 배열로 반환한다.

성공 예시:

```json
{
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "status": "completed",
  "results": [
    {
      "factory_id": "factory-a",
      "status": "success",
      "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json",
      "report_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report.md"
    },
    {
      "factory_id": "factory-b",
      "status": "success",
      "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-b/report-context.json",
      "report_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-b/report.md"
    },
    {
      "factory_id": "factory-c",
      "status": "success",
      "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-c/report-context.json",
      "report_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-c/report.md"
    }
  ]
}
```

부분 실패 예시:

```json
{
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "status": "partial_success",
  "results": [
    {
      "factory_id": "factory-a",
      "status": "success",
      "report_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report.md"
    },
    {
      "factory_id": "factory-b",
      "status": "failed",
      "stage": "GenerateFactoryReport",
      "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-b/report-context.json",
      "error": "Bedrock invocation failed"
    },
    {
      "factory_id": "factory-c",
      "status": "insufficient_data",
      "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-c/report-context.json",
      "reason": "factory_state_collection_rate below minimum threshold"
    }
  ]
}
```

## Step Functions State Machine 설계

권장 state 구성:

```text
Start
  -> PrepareReportWindow
  -> ProcessFactories Map
      -> ProcessHours Map
          -> AggregateFactoryHour
      -> MergeFactoryDaily
      -> GenerateFactoryReport
      -> FactoryDone
  -> Done
```

권장 retry:

| State | Retry 대상 | 정책 |
| --- | --- | --- |
| `AggregateFactoryHour` | S3 transient error, Lambda service error | max 2~3, exponential backoff |
| `MergeFactoryDaily` | S3 transient error | max 2 |
| `GenerateFactoryReport` | Bedrock throttling/transient error | max 2, longer backoff |

권장 catch:

| 위치 | 처리 |
| --- | --- |
| Hour Map item | 특정 hour 실패를 factory 실패로 올릴지, empty/failed hour로 둘지 구현 전 선택 |
| Factory Map branch | factory별 실패를 결과 객체로 반환하고 다른 factory는 계속 진행 |
| State machine root | 예상 밖 오류만 전체 실패 처리 |

MVP 권장값:

```text
특정 hour S3 prefix 없음: empty summary로 성공 처리
특정 hour Lambda 예외: retry 후 실패 시 factory failed
특정 factory insufficient data: report-context 생성 후 report.md에는 insufficient_data 표시
Bedrock 실패: report-context는 남기고 report.md는 생성하지 않음
```

## S3 출력 구조

최종 출력 구조:

```text
reports/daily/yyyy=2026/mm=01/dd=01/
  factory-a/
    intermediate/
      hourly/
        hh=00.json
        hh=01.json
        ...
        hh=23.json
    factory-daily-summary.json
    report-context.json
    report.md
    generation-metadata.json
  factory-b/
    intermediate/
      hourly/
        hh=00.json
        ...
        hh=23.json
    factory-daily-summary.json
    report-context.json
    report.md
    generation-metadata.json
  factory-c/
    intermediate/
      hourly/
        hh=00.json
        ...
        hh=23.json
    factory-daily-summary.json
    report-context.json
    report.md
    generation-metadata.json
```

MVP에서 `intermediate/hourly/`는 삭제하지 않는다. 운영자가 보고서 문장의 근거를 추적할 수 있어야 하기 때문이다.

## 구현 리소스 목록

필요 AWS 리소스:

| 리소스 | 이름 예시 | 설명 |
| --- | --- | --- |
| EventBridge Scheduler | `aegis-daily-factory-report-schedule` | 매일 00:30 KST 실행 |
| Step Functions State Machine | `DailyFactoryReportStateMachine` | 전체 workflow orchestration |
| Lambda | `PrepareReportWindow` | 날짜/window/output prefix 계산 |
| Lambda | `AggregateFactoryHour` | hour 단위 S3 processed 집계 |
| Lambda | `MergeFactoryDaily` | daily summary/context 생성 |
| Lambda | `GenerateFactoryReport` | Bedrock 호출 및 report 저장 |
| IAM Role | reporting Lambda role | S3 read/write, logs, Bedrock 권한 |
| IAM Role | Step Functions role | Lambda invoke 권한 |
| S3 prefix | `reports/daily/` | 보고서 산출물 저장 |
| CloudWatch Log Groups | Lambda별 log group | 실행 로그 |

필요 IAM 권한:

```text
s3:ListBucket on aegis-bucket-data with processed/ and reports/ prefix condition
s3:GetObject on processed/* and reports/daily/*
s3:PutObject on reports/daily/*
bedrock:InvokeModel or bedrock:Converse on selected model
logs:CreateLogGroup
logs:CreateLogStream
logs:PutLogEvents
lambda:InvokeFunction for Step Functions role
states:StartExecution for EventBridge Scheduler role
```

## 구현 순서

새 세션에서 구현할 때는 아래 순서로 진행한다.

1. `apps/daily-report-generator/` 또는 `apps/daily-factory-report/` 디렉터리를 만든다.
2. 공통 S3 reader/reducer 유틸을 먼저 작성한다.
3. `AggregateFactoryHour` 단위 테스트를 작성한다.
4. 샘플 processed JSON fixture를 만든다.
5. `AggregateFactoryHour`가 평균뿐 아니라 max/p95/p05, threshold window, spike event, evidence id를 생성하는지 검증한다.
6. `MergeFactoryDaily` 단위 테스트를 작성한다.
7. hour 경계 이벤트 병합 테스트를 작성한다.
8. severity score top N 선정 테스트를 작성한다.
9. `report-context.json` schema 테스트를 작성한다.
10. `GenerateFactoryReport`는 Bedrock client를 mock으로 시작한다.
11. Bedrock output validation 테스트를 작성한다.
12. Terraform에는 Lambda 4개, Step Functions, EventBridge Scheduler, IAM을 추가한다.
13. dev 환경에서 하루치가 아니라 1~2시간 fixture로 먼저 실행한다.
14. 이후 24시간 전체 fixture 또는 실제 S3 prefix로 dry run한다.
15. CloudWatch log volume과 Lambda duration을 확인한 뒤 concurrency와 timeout을 조정한다.

권장 Lambda timeout/memory 초기값:

| Lambda | Memory | Timeout |
| --- | ---: | ---: |
| `PrepareReportWindow` | 128MB | 30s |
| `AggregateFactoryHour` | 1024MB | 5m |
| `MergeFactoryDaily` | 512MB | 2m |
| `GenerateFactoryReport` | 512MB | 3m |

`AggregateFactoryHour`가 실제 데이터에서 3분을 자주 넘으면 S3 GET concurrency, prefix 계산, reducer 구현을 먼저 점검한다.

## 보고서 품질을 위한 필수 보강 기준

이 파이프라인은 hourly 처리 구조를 사용하지만, 보고서 품질을 위해 아래 기준을 반드시 지킨다.

| 보강 기준 | 이유 | 처리 위치 |
| --- | --- | --- |
| hour 경계 이벤트 병합 | `14:58~15:07` 같은 이벤트가 두 시간대로 쪼개지는 것을 방지 | `MergeFactoryDaily` |
| severity score | 이벤트가 많을 때 운영상 중요한 이벤트를 우선 노출 | `AggregateFactoryHour`, `MergeFactoryDaily` |
| factory interpretation mode | 실제 운영형 `factory-a`와 dummy 테스트베드 `factory-b/c` 해석 분리 | `MergeFactoryDaily` |
| data quality detail | 수집률 평균만으로는 긴 공백이나 late arrival을 설명할 수 없음 | `AggregateFactoryHour`, `MergeFactoryDaily` |
| evidence 보존 | 보고서 문장과 원본 처리 결과를 추적 가능하게 유지 | 모든 summary/context 단계 |
| Bedrock output validation | LLM이 숫자, 날짜, factory ID를 바꾸는 오류 방지 | `GenerateFactoryReport` |

이 기준이 빠지면 hourly summary가 평균화된 리포트로 변질될 수 있으므로 MVP 구현의 acceptance criteria에 포함한다.

## Event Merge and Severity Scoring

### Hour Boundary Event Merge

`MergeFactoryDaily`는 hour별 summary의 이벤트를 시간순으로 정렬한 뒤, 인접한 이벤트가 같은 현상을 가리키면 하나의 daily event로 병합한다.

병합 기준 초안:

- `type`이 같다.
- `severity`가 같거나 더 높은 severity로 승격 가능하다.
- 두 이벤트 사이 gap이 120초 이하이다.
- 주요 원인(`top_causes`, `source_type`, `node_id`, `workload_name`)이 같다.
- 같은 factory 안에서 발생했다.

예시:

```text
14:58~14:59 temperature_spike
15:00~15:07 temperature_spike
-> 14:58~15:07 temperature_spike
```

병합 후 event에는 아래를 남긴다.

- 전체 `time_range`
- 병합된 duration
- 가장 나쁜 severity
- 전체 구간의 max/min 값
- 합쳐진 evidence message IDs 또는 S3 keys

### Severity Score

보고서에는 모든 이벤트를 넣지 않는다. Lambda가 severity score를 계산해 상위 이벤트만 context에 포함한다.

초기 점수 기준:

```text
base severity:
  info = 10
  warning = 50
  danger = 80
  critical = 90

additional score:
  duration_seconds / 60, 최대 20점
  risk min_score가 낮을수록 최대 20점
  data gap max_gap_seconds가 길수록 최대 15점
  같은 type 반복 발생 시 최대 10점
  evidence가 충분하면 +5점
```

`severity_score`는 리포트 노출 순서와 `recommended_checks.priority` 산정에 사용한다.

```json
{
  "event_id": "factory-a-20260101-151000-risk-degradation",
  "severity": "warning",
  "severity_score": 72,
  "type": "risk_degradation",
  "time_range": "15:10~15:25",
  "duration_seconds": 900,
  "evidence": {
    "message_ids": ["..."],
    "s3_keys": ["processed/factory-a/risk_score/..."]
  }
}
```

### Event Top N Policy

- `danger` 또는 `critical` 이벤트는 가능한 한 모두 보존한다.
- `warning` 이벤트는 severity score 상위 순으로 제한한다.
- `report-context.json`에는 기본 최대 10개 이벤트를 넣는다.
- 잘린 이벤트 수는 `events_omitted_count`로 남긴다.

## Report Context and Generation Contract

MVP에서는 `BuildFactoryReportContext`, `GenerateFactoryReportWithBedrock`, `ValidateBedrockOutput`, `RenderFactoryReportDocument`, `SaveFactoryReport`를 별도 Lambda로 만들지 않는다.

역할 통합 기준:

| 기존 세부 역할 | MVP 처리 위치 |
| --- | --- |
| `BuildFactoryReportContext` | `MergeFactoryDaily` 내부 |
| `GenerateFactoryReportWithBedrock` | `GenerateFactoryReport` 내부 |
| `ValidateBedrockOutput` | `GenerateFactoryReport` 내부 |
| `RenderFactoryReportDocument` | `GenerateFactoryReport` 내부, Markdown만 기본 지원 |
| `SaveFactoryReport` | `GenerateFactoryReport` 내부 |

확장 시 DOCX/PDF 렌더링이나 별도 검증이 커지면 위 역할을 다시 Lambda로 분리할 수 있다. MVP 구현은 Lambda 수보다 생성 흐름의 안정성과 명확성을 우선한다.

### Report Context 생성

`MergeFactoryDaily`는 daily summary를 만들고, 같은 실행 안에서 Bedrock 입력용 `report-context.json`을 생성한다.

역할:

- Bedrock 입력 schema 생성
- 권장 확인 항목 생성
- 데이터 한계 생성
- 너무 많은 이벤트가 있을 경우 상위 N개로 제한
- 문자열 길이와 token 크기 제한
- factory interpretation mode 포함
- `report-context.json` 저장

출력:

```text
s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json
```

Bedrock 입력 context 예시:

```json
{
  "schema_version": "0.1.0",
  "report_date": "2026-01-01",
  "generated_at": "2026-01-02T00:30:00+09:00",
  "factory_id": "factory-a",
  "factory_profile": {
    "environment_type": "physical-rpi",
    "data_origin": "real-edge",
    "interpretation_mode": "production-edge"
  },
  "report_type": "daily_factory_operations_draft",
  "risk": {
    "avg_score": 87.1,
    "min_score": 51.2,
    "max_score": 99.0,
    "dominant_level": "normal",
    "worst_level": "warning",
    "warning_minutes": 35,
    "danger_minutes": 0,
    "worst_periods": [
      {
        "time_range": "15:10~15:25",
        "min_score": 51.2,
        "top_causes": ["temperature", "fall_score"]
      }
    ]
  },
  "factory_state": {
    "temperature_avg": 27.4,
    "temperature_max": 42.8,
    "temperature_p95": 38.6,
    "temperature_over_threshold_minutes": 12,
    "humidity_avg": 61.2,
    "humidity_max": 72.5,
    "max_fire_score": 0.1,
    "max_fall_score": 0.91,
    "fall_score_p95": 0.42,
    "fall_score_over_threshold_seconds": 120,
    "max_bend_score": 0.33,
    "abnormal_sound_count": 0
  },
  "infra": {
    "node_not_ready_count": 1,
    "node_not_ready_minutes": 3,
    "workload_restart_total": 4,
    "unhealthy_workload_minutes": 0
  },
  "pipeline": {
    "factory_state_expected_count": 28800,
    "factory_state_actual_count": 28760,
    "infra_state_expected_count": 4320,
    "infra_state_actual_count": 4298,
    "factory_state_collection_rate": 0.9986,
    "infra_state_collection_rate": 0.9949,
    "data_gap_count": 2,
    "max_gap_minutes": 7,
    "pipeline_warning_minutes": 9,
    "pipeline_critical_minutes": 0
  },
  "events": [
    {
      "time_range": "15:10~15:25",
      "severity": "warning",
      "severity_score": 72,
      "type": "risk_degradation",
      "summary": "Risk Score dropped to 51.2",
      "evidence": {
        "temperature_max": 42.8,
        "max_fall_score": 0.91,
        "message_ids": ["factory-a:factory_state:worker2:2026-01-01T06:10:03Z"]
      }
    },
    {
      "time_range": "13:20~13:27",
      "severity": "warning",
      "severity_score": 65,
      "type": "data_gap",
      "summary": "infra_state missing for 7 minutes"
    }
  ],
  "recommended_checks": [
    {
      "priority": "high",
      "reason": "Risk Score dropped to warning level for 15 minutes",
      "check": "15:10~15:25 온도 상승과 fall_score 증가 원인 확인"
    },
    {
      "priority": "medium",
      "reason": "infra_state missing for 7 minutes",
      "check": "13:20~13:27 edge-iot-publisher 로그와 K3s node 상태 확인"
    }
  ],
  "limitations": [
    "이 보고서는 S3 processed 데이터 기준으로 생성된 운영 리포트 초안이다.",
    "원인 판단은 운영자 검토가 필요하다.",
    "S3 raw 원본 재처리는 MVP 보고서 생성 범위에 포함하지 않았다."
  ]
}
```

Context 제한:

- `events`는 기본 최대 10개만 포함한다.
- 잘린 이벤트 수는 `events_omitted_count`로 남긴다.
- raw payload 전체는 포함하지 않는다.
- secret, certificate, token, private key는 포함하지 않는다.
- factory별 input token은 `8k~15k` 범위를 목표로 한다.

## Factory Interpretation and Data Quality

### Factory Interpretation Mode

보고서는 factory 성격에 따라 문장 해석을 달리해야 한다. `MergeFactoryDaily`는 `report-context.json`에 아래 필드를 반드시 포함한다.

```json
{
  "factory_id": "factory-b",
  "factory_profile": {
    "environment_type": "vm-mac",
    "data_origin": "dummy-generator",
    "interpretation_mode": "testbed"
  }
}
```

초기 기준:

| factory | environment_type | data_origin | interpretation_mode |
| --- | --- | --- | --- |
| `factory-a` | `physical-rpi` | `real-edge` | `production-edge` |
| `factory-b` | `vm-mac` | `dummy-generator` | `testbed` |
| `factory-c` | `vm-windows` | `dummy-generator` | `testbed` |

Bedrock 프롬프트는 `interpretation_mode=testbed`인 경우 실제 현장 장애로 단정하지 않고, dummy scenario 또는 테스트베드 조건을 먼저 확인하라고 표현해야 한다.

### Data Quality Fields

수집률만으로 데이터 품질을 판단하지 않는다. context에는 아래 필드를 포함한다.

- `factory_state_collection_rate`
- `infra_state_collection_rate`
- `data_gap_count`
- `max_gap_minutes`
- `late_arrival_count`
- `duplicate_message_count`
- `out_of_order_count`
- `insufficient_data`

보고서에는 정상인 경우에도 데이터 품질 근거를 적는다. 예를 들어 `danger` 이벤트가 없어도 최대 데이터 공백과 수집률을 함께 표시한다.

### Bedrock 호출과 보고서 생성

`GenerateFactoryReport`는 `report-context.json`을 읽어 Bedrock Runtime `InvokeModel` 또는 Converse API를 호출한다.

Bedrock에는 원본 S3 객체 전체를 보내지 않는다. 입력은 `report-context.json` 하나다.

프롬프트 기본 규칙:

```text
너는 Aegis-Pi 운영 보고서 작성 보조자다.
아래 JSON만 근거로 factory별 일일 운영 보고서 초안을 한국어로 작성한다.
JSON에 없는 사실을 만들지 마라.
수치와 시간은 JSON 값을 그대로 사용한다.
원인 확정이 어려운 경우 "추정" 또는 "확인 필요"라고 적는다.
보고서 마지막에 데이터 한계와 운영자 검토 필요 문구를 포함한다.
```

출력 섹션:

```markdown
# Aegis-Pi factory-a 일일 운영 보고서 - 2026-01-01

## 1. 요약
## 2. Risk 상태
## 3. 센서 및 AI 상태
## 4. 인프라 상태
## 5. 데이터 파이프라인 상태
## 6. 주요 이벤트
## 7. 확인 필요 항목
## 8. 데이터 한계
```

### Report Render and Save

MVP 기본 출력은 Markdown이다. `GenerateFactoryReport`가 Bedrock 출력과 `report-context.json`의 핵심 수치를 검증한 뒤 S3에 저장한다.

출력 경로:

```text
s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report.md
s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json
s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=01/dd=01/factory-a/factory-daily-summary.json
s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=01/dd=01/factory-a/generation-metadata.json
```

선택 저장:

```text
s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=01/dd=01/factory-a/bedrock-response.json
```

`bedrock-response.json`은 토큰 사용량, 모델 ID, stop reason, 생성 시각 등 추적 정보가 필요할 때 저장한다. 민감한 prompt나 불필요한 원문 데이터 저장은 피한다.

정확한 수치, 표, 이벤트 목록은 가능한 한 Lambda가 context 값으로 렌더링하거나 검증한다. Bedrock이 수치와 날짜를 임의로 바꾸는 경우 `validation_status=failed`로 처리한다.

## DOCX/PDF 확장 산출물

DOCX/PDF는 MVP 기본 산출물이 아니라 확장 범위다. 다만 초기 설계와 S3 경로는 미리 열어둔다.

### DOCX

DOCX는 템플릿 기반 생성이 가장 안정적이다.

```text
templates/daily_factory_report.docx
  + report-context.json
  + Bedrock generated sections
  -> report.docx
```

DOCX 템플릿에는 아래와 같은 placeholder를 둘 수 있다.

```text
{{ factory_id }}
{{ report_date }}
{{ summary }}
{{ risk.avg_score }}
{{ risk.min_score }}
{{ risk_analysis }}
{{ recommended_checks }}
```

정확한 수치와 표는 Lambda가 채우고, 자연어 문단만 Bedrock 출력 값을 사용한다.

### PDF

PDF는 아래 두 경로 중 하나를 선택한다.

```text
A안: HTML template -> PDF 변환
B안: DOCX -> PDF 변환
```

MVP 확장 우선순위는 DOCX가 PDF보다 높다. PDF는 Lambda 패키징 난도가 높을 수 있으므로, 구현 전 container image 또는 Lambda Layer 전략을 확정한다.

## S3 출력 구조

factory별 보고서 기준 출력 prefix는 아래로 고정한다.

```text
reports/daily/yyyy={YYYY}/mm={MM}/dd={DD}/{factory_id}/
```

전체 예시:

```text
reports/daily/yyyy=2026/mm=01/dd=01/factory-a/
  report.md
  report.docx                            # extension
  report.pdf                             # extension
  report-context.json
  factory-daily-summary.json
  bedrock-response.json                 # optional
  intermediate/
    hourly/
      hh=00.json
      hh=01.json
      ...
      hh=23.json

reports/daily/yyyy=2026/mm=01/dd=01/factory-b/
  report.md
  report.docx                            # extension
  report.pdf                             # extension
  report-context.json
  factory-daily-summary.json
  intermediate/hourly/...

reports/daily/yyyy=2026/mm=01/dd=01/factory-c/
  report.md
  report.docx                            # extension
  report.pdf                             # extension
  report-context.json
  factory-daily-summary.json
  intermediate/hourly/...
```

## 보고서 섹션별 데이터 정의

### 1. 요약

필수 context 필드:

- `factory_id`
- `report_date`
- `environment_type`
- `risk.dominant_level`
- `risk.worst_level`
- `risk.min_score`
- `pipeline.data_gap_count`
- `events` 상위 3개
- `recommended_checks` 상위 3개

### 2. Risk 상태

필수 context 필드:

- `risk.avg_score`
- `risk.min_score`
- `risk.max_score`
- `risk.final_score`
- `risk.dominant_level`
- `risk.worst_level`
- `risk.warning_minutes`
- `risk.danger_minutes`
- `risk.worst_periods`
- `risk.top_causes`

계산 기준:

- 평균/최소/최대는 `risk_score/` processed object 기준
- p05 score와 최악 구간을 함께 저장해 평균 smoothing을 방지
- warning/danger minutes는 Risk level 또는 score threshold 기준
- top causes는 `risk.top_causes` 또는 processed risk object의 원인 필드 기준
- `worst_periods`에는 대표 evidence message_id 또는 S3 key를 포함

### 3. 센서 및 AI 상태

필수 context 필드:

- `factory_state.temperature_avg`
- `factory_state.temperature_max`
- `factory_state.temperature_over_threshold_minutes`
- `factory_state.temperature_p95`
- `factory_state.spike_events`
- `factory_state.humidity_avg`
- `factory_state.humidity_max`
- `factory_state.max_fire_score`
- `factory_state.max_fall_score`
- `factory_state.fall_score_p95`
- `factory_state.fall_score_over_threshold_seconds`
- `factory_state.max_bend_score`
- `factory_state.abnormal_sound_count`

threshold는 최초 MVP에서 `configs/runtime/runtime-config.yaml` 또는 `docs/product/02_requirements_definition.md`의 기준을 따른다. 구현 전 실제 config 위치를 확인한다.

### 4. 인프라 상태

필수 context 필드:

- `infra.node_not_ready_count`
- `infra.node_not_ready_minutes`
- `infra.workload_restart_total`
- `infra.unhealthy_workload_minutes`

입력은 `infra_state/` processed object를 우선한다.

### 5. 데이터 파이프라인 상태

필수 context 필드:

- `pipeline.factory_state_expected_count`
- `pipeline.factory_state_actual_count`
- `pipeline.infra_state_expected_count`
- `pipeline.infra_state_actual_count`
- `pipeline.factory_state_collection_rate`
- `pipeline.infra_state_collection_rate`
- `pipeline.data_gap_count`
- `pipeline.max_gap_minutes`
- `pipeline.pipeline_warning_minutes`
- `pipeline.pipeline_critical_minutes`

expected count 기준:

```text
factory_state: 3초 주기 -> 1시간 1,200건, 하루 28,800건
infra_state: 20초 주기 -> 1시간 180건, 하루 4,320건
```

### 6. 주요 이벤트

이벤트 후보는 Lambda가 생성한다. Bedrock은 이벤트를 새로 만들지 않는다.

MVP 이벤트 타입:

| type | 조건 예시 |
| --- | --- |
| `risk_degradation` | Risk warning/danger 구간 발생 또는 짧은 최악 구간 발생 |
| `sensor_threshold_exceeded` | 온도/습도 threshold 초과 지속 |
| `ai_score_spike` | fire/fall/bend score 기준 초과 |
| `abnormal_sound` | abnormal sound count 증가 |
| `data_gap` | expected 주기 대비 수집 공백 |
| `node_not_ready` | node ready false 발생 |
| `workload_unhealthy` | unhealthy workload 또는 restart 증가 |
| `pipeline_warning` | pipeline warning/critical 지속 |

이벤트 수 제한:

- hourly summary에서는 시간당 최대 5개. 단, danger severity 이벤트는 최대 개수와 별도로 보존 가능
- daily summary에서는 severity와 지속 시간을 기준으로 최대 10개
- report-context에서는 최대 10개

### 7. 확인 필요 항목

권장 확인 항목은 Lambda가 rule 기반으로 만든다. Bedrock은 문장만 다듬는다.

예시 규칙:

```text
if risk.min_score < 60 and risk.warning_minutes >= 10:
  high priority: Risk 저하 시간대의 센서/AI 원인 확인

if pipeline.max_gap_minutes >= 5:
  medium priority: edge-iot-publisher 로그와 K3s node 상태 확인

if infra.workload_restart_total >= 3:
  medium priority: restart가 증가한 workload 로그 확인

if factory_state.temperature_over_threshold_minutes >= 10:
  high priority: 온도 상승 원인 확인
```

### 8. 데이터 한계

항상 포함한다.

기본 문구:

- 이 보고서는 S3 processed 데이터 기준의 운영 리포트 초안이다.
- S3 raw 원본 전체 재처리는 MVP 보고서 생성 범위에 포함하지 않았다.
- 원인 판단과 조치 여부는 운영자 검토가 필요하다.
- factory-b/c는 테스트베드 dummy data 특성이 있으므로 실제 현장 센서 해석과 구분한다.

## Lambda 역할 정의

MVP Lambda는 아래 4개로 고정한다.

```text
PrepareReportWindow
AggregateFactoryHour
MergeFactoryDaily
GenerateFactoryReport
```

### PrepareReportWindow

입력:

```json
{
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "factories": ["factory-a", "factory-b", "factory-c"]
}
```

출력:

- KST/UTC report window
- factories
- hour_items
- S3 input partition hints
- output prefix
- Factory Map에서 사용할 `factory_items`

성공 기준:

- `report_date`가 명확해야 한다.
- `timezone` 기본값은 `Asia/Seoul`이다.
- `hour_items`는 항상 `00`~`23`의 24개 item이며 각 item은 `hour_window`를 포함한다.
- KST 하루가 UTC 두 날짜에 걸칠 수 있음을 반영한다.

### AggregateFactoryHour

입력:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "hour": "15",
  "hour_window": {
    "start_kst": "2026-01-01T15:00:00+09:00",
    "end_kst": "2026-01-01T15:59:59+09:00"
  },
  "datasets": ["factory_state", "risk_score", "infra_state"],
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
}
```

출력:

- hourly summary S3 key
- status: `success`, `empty`, `failed`
- input counts
- event count

실패 처리:

- 해당 hour 데이터가 없어도 실패하지 않고 empty summary를 생성한다.
- S3 prefix가 없어도 empty summary를 생성한다.
- S3 read 자체가 실패하면 retry 후 실패로 표시한다.
- JSON parse 실패 record는 `invalid_records`로 집계하고 나머지 record 처리는 계속한다.

성공 기준:

- 평균뿐 아니라 max, p95, p05, threshold window, spike event, evidence id를 생성한다.
- object별 로그를 남기지 않는다.
- 원본 records 배열 전체를 메모리에 장시간 보관하지 않는다.

### MergeFactoryDaily

입력:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "hour_results": [
    {
      "hour": "00",
      "status": "success",
      "summary_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/intermediate/hourly/hh=00.json"
    }
  ],
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
}
```

출력:

- `factory-daily-summary.json` S3 key
- `report-context.json` S3 key
- status: `success`, `insufficient_data`, `failed`

성공 기준:

- 24개 hour summary를 병합한다.
- hour 경계 이벤트를 병합한다.
- severity score를 계산하고 top event N개를 고른다.
- factory interpretation mode를 context에 포함한다.
- recommended checks와 limitations를 생성한다.

### GenerateFactoryReport

입력:

```json
{
  "factory_id": "factory-a",
  "report_date": "2026-01-01",
  "timezone": "Asia/Seoul",
  "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json",
  "output_prefix": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a"
}
```

출력:

- `report.md` S3 key
- `generation-metadata.json` S3 key
- validation status

성공 기준:

- Bedrock에는 `report-context.json`만 전달한다.
- Bedrock 출력은 저장 전 invariant 검증을 통과해야 한다.
- Markdown 보고서를 저장한다.
- DOCX/PDF는 확장 범위로 남긴다.

## Bedrock Output Validation

Bedrock 출력은 최종 저장 전에 검증한다. 검증 실패 시 재시도하거나, `report-context.json`만 저장하고 보고서 생성 실패로 표시한다.

검증 기준:

- `factory_id`가 context와 일치한다.
- `report_date`가 context와 일치한다.
- 핵심 수치가 context 값과 일치한다. 최소 검증 대상은 `risk.min_score`, `risk.avg_score`, `risk.warning_minutes`, `risk.danger_minutes`, `pipeline.max_gap_minutes`다.
- context에 없는 factory, 날짜, 원인을 새로 만들지 않는다.
- `production-edge`와 `testbed` 해석 모드를 혼동하지 않는다.
- 금지된 단정 표현을 피한다. 예: `확정`, `반드시 고장`, `자동 조치 완료`.

검증 구현은 완전한 자연어 검증이 아니라 핵심 invariant 검사로 시작한다. `GenerateFactoryReport`가 수치 표를 context 값으로 직접 렌더링하거나 저장 전 대조하면, Bedrock이 수치를 임의 변경할 위험을 줄일 수 있다.

검증 실패 결과 예시:

```json
{
  "factory_id": "factory-a",
  "status": "failed",
  "stage": "GenerateFactoryReport.validation",
  "reason": "risk.min_score mismatch",
  "expected": 51.2,
  "found": 51.5
}
```

## Step Functions 실패/재시도 기준

- `AggregateFactoryHour`: S3 transient error는 retry한다.
- 특정 hour 데이터 없음은 정상 empty summary로 처리한다.
- 특정 factory 전체 데이터가 없으면 해당 factory 보고서는 `insufficient_data` 상태로 생성한다.
- Bedrock 호출 실패 시 해당 factory의 `report-context.json`은 남기고 `report.md`는 생성 실패 상태로 기록한다.
- factory-a 실패가 factory-b/c 생성을 막지 않도록 factory Map 내부에 Catch를 둔다.

factory별 결과 상태 예시:

```json
{
  "factory_id": "factory-a",
  "status": "success",
  "report_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report.md"
}
```

실패 예시:

```json
{
  "factory_id": "factory-b",
  "status": "failed",
  "stage": "GenerateFactoryReport",
  "context_key": "reports/daily/yyyy=2026/mm=01/dd=01/factory-b/report-context.json",
  "error": "Bedrock invocation failed"
}
```

## 비용 기준

이 비용 기준은 `Factory x Hour Map` 구조를 기준으로 한다.

기준:

- Region: `ap-south-1` 기준 추정
- 실행 주기: 하루 1회
- 대상 factory: `factory-a`, `factory-b`, `factory-c`
- 무료 티어: 미적용
- 저장소: S3 Standard
- Bedrock: on-demand token 과금

주의:

실제 비용은 region, Lambda duration, S3 object 수, Bedrock model, prompt/context token 수에 따라 달라진다. 이 섹션은 MVP 설계 판단을 위한 추정이다.
Bedrock model availability와 account-level model access는 `ap-south-1`에서 배포 전 별도 확인한다.

MVP 규모 가정:

```text
factory: 3개
hourly aggregation: 3 * 24 = 72회/day
보고서 생성: factory별 1개/day
```

입력 데이터 규모:

```text
factory_state: 3초 주기 = 28,800 objects/factory/day
risk_score: 3초 주기 = 28,800 objects/factory/day
infra_state: 20초 주기 = 4,320 objects/factory/day

보고서 기본 입력:
61,920 objects/factory/day
185,760 objects/day for 3 factories
```

`state_snapshot/`은 MVP 기본 입력에서 제외한다.

비용 발생 항목:

- EventBridge Scheduler: 하루 1회 invocation
- Step Functions Standard: state transition 수
- Lambda: invocation + GB-second
- S3: processed GET/LIST, reports PUT/storage
- CloudWatch Logs
- Bedrock: input/output token

### Lambda 비용

후보 1 기준 Lambda invocation:

```text
PrepareReportWindow: 1회/day
AggregateFactoryHour: 3 factories * 24 hours = 72회/day
MergeFactoryDaily: 3회/day
GenerateFactoryReport: 3회/day

총 Lambda invocation: 79회/day
```

현실적 MVP 추정:

| Lambda | 메모리 | 평균 실행 시간 | 횟수/day | GB-second/day |
| --- | ---: | ---: | ---: | ---: |
| PrepareReportWindow | 128MB | 1s | 1 | 0.125 |
| AggregateFactoryHour | 1024MB | 30s | 72 | 2,160 |
| MergeFactoryDaily | 512MB | 5s | 3 | 7.5 |
| GenerateFactoryReport | 512MB | 10s | 3 | 15 |
| 합계 |  |  | 79 | 2,182.625 |

Lambda 비용 추정:

```text
Request cost: 약 $0.000016/day
Duration cost: 약 $0.036/day

월 30일 기준: 약 $1.09/month
```

보수적 추정:

| 시나리오 | 하루 비용 | 월 30일 비용 |
| --- | ---: | ---: |
| AggregateFactoryHour 평균 30초 | 약 $0.036/day | 약 $1.09/month |
| AggregateFactoryHour 평균 60초 | 약 $0.073/day | 약 $2.18/month |
| AggregateFactoryHour 평균 120초 | 약 $0.145/day | 약 $4.35/month |

### Step Functions 비용

Step Functions Standard는 state transition 기준으로 과금된다.

MVP `Factory x Hour Map` 구조의 transition 수는 구현 세부에 따라 달라지지만, 하루 1회 실행 기준 대략 `100~130 state transitions/day` 수준으로 본다.

```text
100~130 transitions/day * $0.000025
= 약 $0.0025~$0.0033/day
= 약 $0.08~$0.10/month
```

Retry가 많아지면 transition 수가 증가한다.

### S3 비용

기본 입력 object 수:

```text
61,920 objects/factory/day
185,760 objects/day for 3 factories
```

S3 GET:

```text
185,760 GET/day * $0.0004 / 1,000
= 약 $0.074/day
= 약 $2.23/month
```

S3 LIST:

hour별 prefix를 dataset별로 조회한다고 가정한다.

```text
3 factories * 24 hours * 3 datasets = 216 LIST/day
여유 포함 360 LIST/day 가정

360 LIST/day * $0.005 / 1,000
= 약 $0.0018/day
= 약 $0.054/month
```

S3 PUT:

hour summary, daily summary, report context, report output 저장을 합쳐 약 `80 PUT/day`로 가정한다.

```text
80 PUT/day * $0.005 / 1,000
= 약 $0.0004/day
= 약 $0.012/month
```

S3 storage:

보고서와 context 산출물은 작으므로 MVP 비용 산정에서는 무시 가능한 수준이다. 단, `report-context.json`을 지나치게 크게 만들거나 원본 payload를 복사 저장하면 별도 산정이 필요하다.

### CloudWatch Logs 비용

Lambda와 Step Functions 로그는 운영 확인에 필요하지만, payload 본문 또는 object별 처리 로그를 남기면 비용과 노이즈가 커진다.

MVP 로그량 가정:

```text
1~10 MB/day
CloudWatch Logs ingestion: 약 $0.50/GB
```

추정:

```text
약 $0.0005~$0.005/day
약 $0.02~$0.15/month
```

로그 정책:

- Lambda 시작/종료, factory_id, report_date, hour, processed object count, event count, output key만 로깅한다.
- S3 object key 전체 목록은 로깅하지 않는다.
- JSON payload 본문은 로깅하지 않는다.
- 반복되는 정상 처리 로그는 count summary로 대체한다.

### EventBridge Scheduler 비용

하루 1회 schedule invocation만 사용한다.

```text
1 invocation/day
30 invocations/month
```

MVP 비용 산정에서는 무시 가능한 수준이다.

### Bedrock 비용

Bedrock 비용은 model과 token 수에 따라 달라진다. MVP는 factory별 보고서를 하루 3개 생성한다.

권장 입력 방식:

- 원본 S3 object를 Bedrock에 직접 넣지 않는다.
- `report-context.json`은 top event, hourly summary, daily metrics 중심으로 compact하게 유지한다.
- factory별 input token은 `8k~15k`, output token은 `1.5k~3k` 범위를 목표로 한다.

Claude 3 Haiku 기준 추정:

```text
3 reports/day
compact context 기준

약 $0.012~$0.025/day
약 $0.35~$0.75/month
```

Claude 3.5 Haiku 기준 추정:

```text
3 reports/day
compact context 기준

약 $0.037~$0.078/day
약 $1.10~$2.35/month
```

보고서 품질을 위해 더 큰 context를 넣거나 재시도를 많이 수행하면 Bedrock 비용이 선형적으로 증가한다.

### 최종 비용 요약

| 항목 | 예상 비용/month |
| --- | ---: |
| Lambda | 약 $1.09~$2.18 |
| Step Functions | 약 $0.08~$0.10 |
| S3 GET/LIST/PUT | 약 $2.29 |
| CloudWatch Logs | 약 $0.02~$0.15 |
| EventBridge Scheduler | 무시 가능 |
| Bedrock Claude 3 Haiku | 약 $0.35~$0.75 |
| Bedrock Claude 3.5 Haiku | 약 $1.10~$2.35 |

총액:

| 시나리오 | 월 예상 비용 |
| --- | ---: |
| Claude 3 Haiku + 현실적 Lambda | 약 $3.8~$5.4/month |
| Claude 3.5 Haiku + 현실적 Lambda | 약 $4.6~$7.0/month |
| Lambda가 hour당 2분까지 늘어나는 보수 케이스 | 약 $7~$10/month |

결론:

- MVP 기준 전체 비용은 월 $5 안팎으로 예상한다.
- 보수적으로 잡아도 월 $10 이하로 보는 것이 합리적이다.
- Lambda invocation 수보다 S3 GET 수가 비용에 더 큰 영향을 준다.
- CloudWatch에 per-object 로그를 남기면 로그 비용이 불필요하게 증가할 수 있다.

비용을 키우는 요인:

- S3 raw 원본까지 읽음
- `state_snapshot/` 전체를 매번 읽음
- CloudWatch에 payload 전체를 로깅
- factory 수 증가
- 보고서 생성 주기 증가
- Bedrock context token 수 증가
- Bedrock retry 증가

MVP 비용 제어 원칙:

- S3 raw는 읽지 않는다.
- `risk_score/`, `factory_state/`, `infra_state/` 중심으로 읽는다.
- hourly summary와 daily summary를 재사용한다.
- CloudWatch에는 payload 본문을 남기지 않는다.
- report-context 크기를 제한한다.

## 보안/IAM 기준

필요 권한:

- `s3:ListBucket` on `aegis-bucket-data` scoped to `processed/` and `reports/`
- `s3:GetObject` on `processed/*`
- `s3:PutObject` on `reports/daily/*`
- `bedrock:InvokeModel` 또는 Converse API에 필요한 Bedrock Runtime 권한
- CloudWatch Logs write
- Step Functions execution role에서 Lambda invoke 권한

금지:

- secret, certificate, token, private key를 report-context나 report에 포함하지 않는다.
- raw payload 전체를 Bedrock prompt에 넣지 않는다.
- 운영자 개인정보를 포함하지 않는다.

## 구현 위치 기준

구현 위치는 아래 `Implementation Blueprint`를 source of truth로 따른다.

확정 경로:

```text
apps/daily-report-generator/
infra/reporting/
scripts/build/build-reporting.sh
scripts/destroy/destroy-reporting.sh
docs/ops/24_daily_factory_report.md
```

이전 검토에서 언급한 `apps/daily-factory-report/`나 단일 `lambda_function.py` 방식은 사용하지 않는다. Lambda는 4개 함수로 만들되 같은 `apps/daily-report-generator/` package를 공유한다.

## MVP 구현 순서

1. 제품/요구사항 문서 갱신
   - `docs/product/00_mvp_scope.md`: LLM 일일 factory 보고서를 MVP 포함으로 변경
   - `docs/product/02_requirements_definition.md`: 기능 요구사항과 제한 추가
   - `docs/planning/00_project_overview.md`: 후속 항목에서 MVP 포함 항목으로 조정

2. reporting spec 확정
   - 이 문서의 report-context schema를 기준으로 `docs/specs/` 또는 본 문서에 유지
   - 초기에 별도 specs 문서를 만들지 않고 이 문서를 source of truth로 유지해도 됨

3. `apps/daily-report-generator/` 구현
   - S3 processed 샘플 fixture 기반 unit test 작성
   - hourly aggregation 테스트
   - 짧은 spike가 평균에 묻히지 않고 event로 보존되는지 테스트
   - hour 경계 이벤트가 daily merge에서 하나로 병합되는지 테스트
   - severity_score 기반 top N 이벤트 선정 테스트
   - production-edge/testbed interpretation mode 테스트
   - daily merge 테스트
   - context builder 테스트
   - Bedrock client는 mock 테스트
   - Bedrock output validation 테스트

4. `infra/reporting/` 구현
   - Lambda package
   - Step Functions state machine
   - EventBridge Scheduler
   - IAM role/policy
   - CloudWatch log group

5. build/destroy 스크립트 추가
   - `scripts/build/build-reporting.sh`
   - `scripts/destroy/destroy-reporting.sh`

6. 샘플 데이터 기반 로컬 검증
   - S3 없이 fixture로 context 생성
   - report-context 크기 확인
   - Bedrock mock으로 report.md 생성

7. AWS 배포 검증
   - `build-reporting.sh <MFA_OTP>`
   - 수동 Step Functions 실행
   - factory-a report-context/report 생성 확인
   - factory-b/c 생성 확인

8. 운영 문서 추가
   - `docs/ops/24_daily_factory_report.md` 같은 운영 절차 문서 작성
   - 생성/재생성/실패 확인 방법 포함

## Implementation Blueprint

이 섹션은 새 세션에서 실제 파일 생성을 바로 시작하기 위한 구현 지시서다. 이 문서만 보고도 MVP reporting stack을 만들 수 있도록 파일 경로, Lambda package 구조, 환경변수, Terraform 리소스, Step Functions ASL 초안, 테스트 fixture 구조를 고정한다.

### 1. 확정 구현 경로

MVP 구현 경로는 아래로 확정한다.

```text
apps/daily-report-generator/
infra/reporting/
scripts/build/build-reporting.sh
scripts/destroy/destroy-reporting.sh
docs/ops/24_daily_factory_report.md
```

선택하지 않는 경로:

```text
apps/daily-factory-report/          # 사용하지 않음
infra/data-pipeline/                # 기존 ingestion pipeline이므로 reporting 리소스를 넣지 않음
infra/foundation/                   # 영구 foundation 리소스만 유지
```

이유:

- reporting stack은 S3 processed를 읽고 보고서를 생성하는 batch/reporting layer다.
- 기존 data processor Lambda와 배포 주기, 장애 영향 범위가 다르다.
- `infra/reporting/`을 별도 Terraform root module로 두면 reporting 기능만 build/destroy할 수 있다.

### 2. Lambda 패키지 구조

`apps/daily-report-generator/`는 하나의 Python package 안에 4개 Lambda handler를 둔다. Lambda 함수는 4개지만 코드 package는 같은 디렉터리에서 빌드한다.

```text
apps/daily-report-generator/
  README.md
  requirements.txt
  lambda_prepare_report_window.py
  lambda_aggregate_factory_hour.py
  lambda_merge_factory_daily.py
  lambda_generate_factory_report.py
  report_generator/
    __init__.py
    config.py
    time_window.py
    s3_keys.py
    s3_reader.py
    json_loader.py
    reducers.py
    aggregate_hour.py
    event_detection.py
    severity.py
    merge_daily.py
    context_builder.py
    prompt_builder.py
    bedrock_client.py
    validation.py
    report_renderer.py
    s3_writer.py
  tests/
    __init__.py
    fixtures/
      processed/
        factory-a/
          factory_state/
          risk_score/
          infra_state/
      hourly/
      context/
    test_time_window.py
    test_s3_keys.py
    test_aggregate_hour.py
    test_event_detection.py
    test_severity.py
    test_merge_daily.py
    test_context_builder.py
    test_prompt_builder.py
    test_validation.py
```

Handler mapping:

| Lambda | Handler |
| --- | --- |
| `PrepareReportWindow` | `lambda_prepare_report_window.handler` |
| `AggregateFactoryHour` | `lambda_aggregate_factory_hour.handler` |
| `MergeFactoryDaily` | `lambda_merge_factory_daily.handler` |
| `GenerateFactoryReport` | `lambda_generate_factory_report.handler` |

공통 모듈 책임:

| Module | 책임 |
| --- | --- |
| `config.py` | 환경변수, threshold, 기본 factory profile 로드 |
| `time_window.py` | KST/UTC report window, hour window 계산 |
| `s3_keys.py` | processed/report S3 prefix 생성 |
| `s3_reader.py` | ListObjectsV2, bounded concurrency GET |
| `json_loader.py` | JSON parse, timestamp 추출, invalid record 처리 |
| `reducers.py` | avg/min/max/p05/p95, duration, gap 계산 |
| `aggregate_hour.py` | hour 단위 summary 생성 orchestration |
| `event_detection.py` | threshold window, spike, data gap 이벤트 탐지 |
| `severity.py` | severity score 계산과 top N 선정 |
| `merge_daily.py` | 24개 hourly summary 병합, hour boundary event merge |
| `context_builder.py` | Bedrock 입력용 compact context 생성 |
| `prompt_builder.py` | Bedrock prompt 생성 |
| `bedrock_client.py` | Bedrock Runtime 호출 wrapper |
| `validation.py` | Bedrock output invariant 검증 |
| `report_renderer.py` | Markdown report rendering |
| `s3_writer.py` | summary/context/report S3 저장 |

### 3. Lambda 환경변수

공통 환경변수:

| Name | Default | 설명 |
| --- | --- | --- |
| `S3_BUCKET_NAME` | `aegis-bucket-data` | processed/report bucket |
| `REPORT_TIMEZONE` | `Asia/Seoul` | report 기준 timezone |
| `REPORT_OUTPUT_PREFIX` | `reports/daily` | 보고서 출력 root prefix |
| `REPORT_DATASETS` | `factory_state,risk_score,infra_state` | 기본 입력 dataset |
| `REPORT_FACTORY_IDS` | `factory-a,factory-b,factory-c` | 기본 factory 목록 |
| `LOG_LEVEL` | `INFO` | Lambda log level |

`AggregateFactoryHour` 환경변수:

| Name | Default | 설명 |
| --- | --- | --- |
| `S3_GET_CONCURRENCY` | `16` | S3 object read 동시성 |
| `MAX_OBJECTS_PER_HOUR` | `10000` | hour 단위 안전 한도 |
| `FACTORY_STATE_INTERVAL_SECONDS` | `3` | expected count 계산 기준 |
| `RISK_SCORE_INTERVAL_SECONDS` | `3` | expected count 계산 기준 |
| `INFRA_STATE_INTERVAL_SECONDS` | `20` | expected count 계산 기준 |
| `RISK_WARNING_SCORE_MAX` | `84.99` | warning duration 계산 기준 |
| `RISK_DANGER_SCORE_MAX` | `49.99` | danger duration 계산 기준 |
| `TEMPERATURE_WARNING_C` | `32` | 온도 threshold |
| `TEMPERATURE_CRITICAL_C` | `38` | 온도 critical threshold |
| `HUMIDITY_WARNING_PERCENT` | `70` | 습도 threshold |
| `HUMIDITY_CRITICAL_PERCENT` | `85` | 습도 critical threshold |
| `AI_SCORE_SPIKE_THRESHOLD` | `0.7` | fire/fall/bend spike 기준 |
| `EVENT_MERGE_GAP_SECONDS` | `120` | 같은 이벤트 병합 gap |

`MergeFactoryDaily` 환경변수:

| Name | Default | 설명 |
| --- | --- | --- |
| `MAX_CONTEXT_EVENTS` | `10` | Bedrock context에 넣을 event 수 |
| `MAX_RECOMMENDED_CHECKS` | `5` | 권장 확인 항목 수 |
| `MIN_FACTORY_STATE_COLLECTION_RATE` | `0.8` | insufficient data 기준 |
| `MIN_INFRA_STATE_COLLECTION_RATE` | `0.8` | insufficient data 기준 |
| `HOURLY_SUMMARY_RETENTION_DAYS` | `30` | 문서상 보존 기준. 실제 lifecycle은 후속 설정 |

`GenerateFactoryReport` 환경변수:

| Name | Default | 설명 |
| --- | --- | --- |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | MVP 기본 모델 |
| `BEDROCK_MAX_TOKENS` | `3000` | 출력 token 제한 |
| `BEDROCK_TEMPERATURE` | `0.2` | 보고서 안정성 우선 |
| `BEDROCK_SAVE_RESPONSE` | `false` | `bedrock-response.json` 저장 여부 |
| `REPORT_OUTPUT_FORMATS` | `md` | MVP는 Markdown만 |
| `MAX_CONTEXT_BYTES` | `120000` | context 크기 안전 한도 |

### 4. Terraform 리소스와 파일 단위 계획

`infra/reporting/` 파일 구조:

```text
infra/reporting/
  README.md
  versions.tf
  providers.tf
  variables.tf
  locals.tf
  data.tf
  iam.tf
  lambda.tf
  stepfunctions.tf
  scheduler.tf
  cloudwatch.tf
  outputs.tf
  terraform.tfvars.example
```

파일별 내용:

| File | 내용 |
| --- | --- |
| `versions.tf` | Terraform/AWS provider version |
| `providers.tf` | AWS provider, region variable |
| `variables.tf` | project, environment, region, bucket, schedule, Bedrock model variables |
| `locals.tf` | name prefix, tags, Lambda names, common env |
| `data.tf` | `data_bucket_name` variable로 기존 S3 bucket 조회 |
| `iam.tf` | Lambda role/policy, Step Functions role, Scheduler role |
| `lambda.tf` | 4개 Lambda function, package file, env, timeout/memory |
| `stepfunctions.tf` | State machine definition |
| `scheduler.tf` | EventBridge Scheduler schedule |
| `cloudwatch.tf` | Lambda log group, retention days |
| `outputs.tf` | state machine ARN, Lambda names, schedule ARN |

권장 Terraform 변수:

```hcl
variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "project_name" {
  type    = string
  default = "aegis"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "data_bucket_name" {
  type    = string
  default = "aegis-bucket-data"
}

variable "report_timezone" {
  type    = string
  default = "Asia/Seoul"
}

variable "report_factory_ids" {
  type    = list(string)
  default = ["factory-a", "factory-b", "factory-c"]
}

variable "bedrock_model_id" {
  type    = string
  default = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "schedule_expression" {
  type    = string
  default = "cron(30 15 * * ? *)"
}
```

`infra/reporting/`은 MVP에서 foundation remote state를 읽지 않는다. `data_bucket_name`을 입력값으로 받고 `data "aws_s3_bucket"`으로 기존 버킷 존재 여부를 확인한다.

권장 이유:

- reporting stack이 필요한 foundation 출력은 현재 S3 bucket name/ARN뿐이다.
- bucket name은 이미 `infra/data-pipeline/`도 variable로 받아 `data.aws_s3_bucket`으로 참조한다.
- local backend의 `../foundation/terraform.tfstate` 경로에 의존하지 않아 CI/다른 작업 디렉터리에서도 적용하기 쉽다.
- foundation은 S3 bucket의 생성/삭제 소유권을 유지하고, reporting은 reports prefix 권한만 가진 소비자로 분리된다.
- 후속으로 AMP workspace ARN, DynamoDB table ARN 등 foundation 출력이 추가로 필요해지면 그때 remote state를 도입한다.

Lambda 설정 초기값:

| Lambda | Memory | Timeout | Reserved concurrency |
| --- | ---: | ---: | ---: |
| `PrepareReportWindow` | 128MB | 30s | unset |
| `AggregateFactoryHour` | 1024MB | 300s | 24 이하 권장 |
| `MergeFactoryDaily` | 512MB | 120s | unset |
| `GenerateFactoryReport` | 512MB | 180s | 3 이하 권장 |

CloudWatch log retention:

```text
14 days for MVP
```

### 5. Lambda 빌드/패키징 기준

빌드 스크립트는 Lambda zip을 아래 경로에 생성한다.

```text
build/reporting/prepare_report_window.zip
build/reporting/aggregate_factory_hour.zip
build/reporting/merge_factory_daily.zip
build/reporting/generate_factory_report.zip
```

패키징 기준:

- Python runtime은 `python3.12`를 사용한다.
- `requirements.txt` 의존성은 zip root에 설치한다.
- `report_generator/` package와 각 `lambda_*.py` handler를 zip root에 포함한다.
- 테스트 파일과 fixture는 zip에 포함하지 않는다.
- 네 Lambda는 같은 source package를 공유해도 되지만 zip 산출물은 함수별로 만든다.
- 함수별 zip을 분리하면 handler/timeout/env 변경과 배포 추적이 명확하다.

`scripts/build/build-reporting.sh` 기본 동작:

```text
1. repo root 확인
2. build/reporting/ 초기화
3. 각 Lambda별 package directory 생성
4. pip install -r apps/daily-report-generator/requirements.txt -t package_dir
5. report_generator/ 복사
6. 대상 lambda_*.py 복사
7. zip 생성
8. terraform -chdir=infra/reporting init/plan/apply 실행
```

`scripts/destroy/destroy-reporting.sh` 기본 동작:

```text
1. repo root 확인
2. terraform -chdir=infra/reporting destroy 실행
3. build/reporting/ 산출물은 삭제하지 않아도 됨
```

### 6. Step Functions ASL 초안

아래 ASL은 구현자가 `templatefile` 또는 `jsonencode`로 Terraform에 넣을 기준 초안이다. 실제 Lambda ARN은 Terraform interpolation으로 치환한다.

```json
{
  "Comment": "Aegis daily factory report generation",
  "StartAt": "PrepareReportWindow",
  "States": {
    "PrepareReportWindow": {
      "Type": "Task",
      "Resource": "${prepare_report_window_lambda_arn}",
      "ResultPath": "$.prepared",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Next": "ProcessFactories"
    },
    "ProcessFactories": {
      "Type": "Map",
      "ItemsPath": "$.prepared.factory_items",
      "MaxConcurrency": 3,
      "ResultPath": "$.factory_results",
      "Iterator": {
        "StartAt": "ProcessHours",
        "States": {
          "ProcessHours": {
            "Type": "Map",
            "ItemsPath": "$.hour_items",
            "MaxConcurrency": 8,
            "Parameters": {
              "factory_id.$": "$.factory_id",
              "report_date.$": "$.report_date",
              "timezone.$": "$.timezone",
              "hour.$": "$$.Map.Item.Value.hour",
              "hour_window.$": "$$.Map.Item.Value.hour_window",
              "datasets.$": "$.datasets",
              "output_prefix.$": "$.output_prefix"
            },
            "ResultPath": "$.hour_results",
            "Iterator": {
              "StartAt": "AggregateFactoryHour",
              "States": {
                "AggregateFactoryHour": {
                  "Type": "Task",
                  "Resource": "${aggregate_factory_hour_lambda_arn}",
                  "Retry": [
                    {
                      "ErrorEquals": ["S3TransientError", "Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                      "IntervalSeconds": 2,
                      "MaxAttempts": 3,
                      "BackoffRate": 2.0
                    }
                  ],
                  "End": true
                }
              }
            },
            "Next": "MergeFactoryDaily"
          },
          "MergeFactoryDaily": {
            "Type": "Task",
            "Resource": "${merge_factory_daily_lambda_arn}",
            "Parameters": {
              "factory_id.$": "$.factory_id",
              "report_date.$": "$.report_date",
              "timezone.$": "$.timezone",
              "output_prefix.$": "$.output_prefix",
              "hour_results.$": "$.hour_results"
            },
            "ResultPath": "$.daily_result",
            "Retry": [
              {
                "ErrorEquals": ["S3TransientError", "Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                "IntervalSeconds": 2,
                "MaxAttempts": 2,
                "BackoffRate": 2.0
              }
            ],
            "Next": "GenerateFactoryReport"
          },
          "GenerateFactoryReport": {
            "Type": "Task",
            "Resource": "${generate_factory_report_lambda_arn}",
            "Parameters": {
              "factory_id.$": "$.factory_id",
              "report_date.$": "$.report_date",
              "timezone.$": "$.timezone",
              "context_key.$": "$.daily_result.context_key",
              "output_prefix.$": "$.output_prefix"
            },
            "ResultPath": "$.report_result",
            "Retry": [
              {
                "ErrorEquals": ["BedrockThrottling", "BedrockTransientError", "Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
                "IntervalSeconds": 5,
                "MaxAttempts": 2,
                "BackoffRate": 2.0
              }
            ],
            "Catch": [
              {
                "ErrorEquals": ["States.ALL"],
                "ResultPath": "$.factory_error",
                "Next": "FactoryFailed"
              }
            ],
            "Next": "FactorySucceeded"
          },
          "FactorySucceeded": {
            "Type": "Pass",
            "Parameters": {
              "factory_id.$": "$.factory_id",
              "status": "success",
              "context_key.$": "$.daily_result.context_key",
              "report_key.$": "$.report_result.report_key"
            },
            "End": true
          },
          "FactoryFailed": {
            "Type": "Pass",
            "Parameters": {
              "factory_id.$": "$.factory_id",
              "status": "failed",
              "error.$": "$.factory_error"
            },
            "End": true
          }
        }
      },
      "Next": "Done"
    },
    "Done": {
      "Type": "Pass",
      "Parameters": {
        "report_date.$": "$.prepared.report_date",
        "timezone.$": "$.prepared.timezone",
        "results.$": "$.factory_results"
      },
      "End": true
    }
  }
}
```

ASL 구현 주의:

- 위 초안은 `PrepareReportWindow`가 `hour_items`를 생성한다는 전제를 따른다. 각 Hour Map item은 `hour`와 `hour_window`를 포함한다.
- Step Functions JSONPath와 `Parameters`는 실제 Terraform apply 전 `asl-validator` 또는 AWS 콘솔 validation으로 확인한다.
- Factory branch의 `Catch`는 factory 단위 실패 격리를 위해 유지한다.
- Hour 실패를 factory 실패로 볼지, failed-hour summary로 볼지는 구현 전 선택하되 MVP 기본값은 factory failed다.

### 7. 테스트 fixture 구조

fixture는 실제 S3 없이 reducer와 merge를 검증하기 위해 둔다.

```text
apps/daily-report-generator/tests/fixtures/
  processed/
    factory-a/
      factory_state/
        2026-01-01T15-00-00Z.json
        2026-01-01T15-00-03Z.json
      risk_score/
        2026-01-01T15-00-00Z.json
        2026-01-01T15-00-03Z.json
      infra_state/
        2026-01-01T15-00-00Z.json
        2026-01-01T15-00-20Z.json
    factory-b/
      factory_state/
      risk_score/
      infra_state/
  hourly/
    factory-a-hh14-summary.json
    factory-a-hh15-summary.json
  context/
    factory-a-report-context.json
    factory-b-report-context.json
```

필수 fixture case:

| Fixture | 목적 |
| --- | --- |
| 정상 hour | count, avg, max, p95 계산 검증 |
| 짧은 spike | 평균에 묻히지 않고 `spike_events` 생성 검증 |
| threshold window | 연속 초과 sample을 event window로 병합 검증 |
| data gap | max gap, gap window, collection rate 검증 |
| duplicate message | duplicate 제거 검증 |
| invalid JSON | invalid count 증가, 나머지 처리 지속 검증 |
| hour boundary event | `14:58~15:07` 병합 검증 |
| insufficient data | collection rate 부족 시 status 검증 |
| testbed factory | `factory-b/c` interpretation mode 검증 |
| Bedrock mismatch | 수치 mismatch validation 실패 검증 |

최소 processed fixture 형태:

```json
{
  "source_message_id": "factory-a:factory_state:worker2:2026-01-01T06:00:00Z",
  "factory_id": "factory-a",
  "source_timestamp": "2026-01-01T06:00:00Z",
  "processed_at": "2026-01-01T06:00:01Z",
  "data": {
    "aggregation_window_seconds": 3,
    "temperature_celsius": 31.2,
    "humidity_percent": 65.1,
    "pressure_hpa": 1011.2,
    "sample_count": 1,
    "fire_score": 0.0,
    "fall_score": 0.1,
    "bend_score": 0.0,
    "abnormal_sound": "none",
    "ai_sample_count": 1
  }
}
```

Risk fixture 형태:

```json
{
  "source_message_id": "factory-a:factory_state:worker2:2026-01-01T06:00:00Z",
  "factory_id": "factory-a",
  "source_timestamp": "2026-01-01T06:00:00Z",
  "processed_at": "2026-01-01T06:00:01Z",
  "data": {
    "temperature_celsius": 31.2,
    "humidity_percent": 65.1,
    "pressure_hpa": 1011.2,
    "fire_score": 0.0,
    "fall_score": 0.1,
    "bend_score": 0.0,
    "abnormal_sound": "none"
  },
  "risk": {
    "score": 91.5,
    "level": "safe",
    "top_causes": []
  },
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 5
  }
}
```

Infra fixture 형태:

```json
{
  "source_message_id": "factory-a:infra_state:cluster:2026-01-01T06:00:00Z",
  "factory_id": "factory-a",
  "source_timestamp": "2026-01-01T06:00:00Z",
  "processed_at": "2026-01-01T06:00:01Z",
  "data": {
    "heartbeat": {
      "agent_status": "alive",
      "last_successful_publish_at": "2026-01-01T06:00:00Z",
      "last_checkpoint_timestamp": "2026-01-01T06:00:00Z",
      "publish_sequence": 12345
    },
    "cluster": {
      "cluster_name": "factory-a",
      "kubernetes_version": "v1.34.6+k3s1"
    },
    "nodes_total": 3,
    "nodes_ready": 3,
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
    "pods_ready": 6,
    "pods_total": 6,
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
        "last_seen_at": "2026-01-01T06:00:00Z"
      },
      "camera": {
        "available": true,
        "last_seen_at": "2026-01-01T06:00:00Z"
      },
      "microphone": {
        "available": true,
        "last_seen_at": "2026-01-01T06:00:00Z"
      }
    }
  },
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 0
  }
}
```

### 8. 구현 체크리스트

문서 기반 구현 완료 체크리스트:

- [x] `apps/daily-report-generator/` package 생성
- [x] 4개 Lambda handler 생성
- [x] 공통 config/time_window/s3_keys 모듈 구현
- [x] S3 reader가 ListObjectsV2 pagination을 처리
- [x] S3 reader가 bounded concurrency GET을 지원
- [x] JSON parse 실패가 전체 Lambda 실패로 이어지지 않음
- [x] `AggregateFactoryHour`가 empty hour summary를 생성
- [x] `AggregateFactoryHour`가 expected/actual count를 계산
- [x] `AggregateFactoryHour`가 avg/min/max/p05/p95를 계산
- [x] spike event와 threshold window가 평균에 묻히지 않음
- [x] evidence message id 또는 S3 key가 summary에 남음
- [x] `MergeFactoryDaily`가 24개 hour summary를 병합
- [x] hour boundary event merge 테스트 통과
- [x] severity score top N 테스트 통과
- [x] factory profile/testbed interpretation mode 포함
- [x] `report-context.json`이 compact context 기준을 만족
- [x] `GenerateFactoryReport`가 Bedrock mock으로 report.md 생성
- [x] Bedrock output invariant validation 구현
- [x] `generation-metadata.json` 저장
- [x] `infra/reporting/` Terraform root module 생성
- [x] Lambda IAM role에 S3/Bedrock/Logs 권한 최소 부여
- [x] Step Functions role에 Lambda invoke 권한 부여
- [x] EventBridge Scheduler role에 `states:StartExecution` 권한 부여
- [x] CloudWatch log retention 14일 설정
- [x] `scripts/build/build-reporting.sh` 추가
- [x] `scripts/destroy/destroy-reporting.sh` 추가
- [x] `docs/ops/24_daily_factory_report.md` 운영 문서 추가
- [x] 1~2시간 fixture dry run 성공
- [ ] 24시간 dry run 성공
- [ ] 실제 S3 prefix 대상 수동 Step Functions 실행 성공
- [ ] factory별 `report-context.json`과 `report.md` 생성 확인

### 9. 다음 구현 세션 권장 순서

로컬 구현은 진행됐으므로 다음 세션에서는 검증과 AWS 실행을 우선한다.

```text
1. 로컬 pytest/compileall 재실행
2. terraform validate 재실행
3. enriched v2 Bedrock 실호출
4. Bedrock 출력 invariant와 보고서 품질 검토
5. 24시간 daily merge 검증
6. reporting stack AWS 배포
7. Step Functions 수동 실행 검증
8. S3 reports/daily 산출물 확인
```

이 순서를 지키면 이미 구현한 reducer/merge/prompt 품질을 실제 Bedrock 출력과 AWS 실행 경로에서 검증할 수 있다.

## Acceptance Criteria

MVP 완료 조건:

- [ ] 매일 1회 factory별 보고서 생성 스케줄이 정의됨
- [ ] `factory-a`, `factory-b`, `factory-c` 각각 `report-context.json` 생성
- [ ] 각 factory별 `report.md` 생성
- [ ] 보고서 입력은 S3 processed 기반이며 S3 raw 원본 전체를 Bedrock에 넣지 않음
- [ ] report-context에 Risk, 센서/AI, 인프라, pipeline, 이벤트, 확인 필요 항목, 한계가 포함됨
- [ ] hourly 처리에서 spike, 최악 구간, threshold 초과 구간, evidence가 평균에 묻히지 않고 보존됨
- [ ] hour 경계에 걸친 이벤트가 daily merge에서 병합됨
- [ ] 이벤트가 severity_score 기준으로 정렬되고 top N 정책이 적용됨
- [ ] factory별 interpretation mode가 context와 prompt에 반영됨
- [ ] Bedrock 출력은 Markdown 또는 구조화 텍스트 섹션 형식
- [ ] 보고서와 context가 S3 `reports/daily/.../{factory_id}/`에 저장됨
- [ ] 확장 범위로 DOCX/PDF 산출물 경로와 렌더링 전략이 문서화됨
- [ ] 특정 factory 보고서 실패가 다른 factory 보고서 생성을 막지 않음
- [ ] Bedrock 출력 후 핵심 수치/date/factory ID invariant 검증이 수행됨
- [ ] CloudWatch Logs에서 factory별 성공/실패 원인을 확인 가능
- [ ] Bedrock 제외 추가 비용 추정이 `docs/ops/15_aws_cost_baseline.md` 또는 별도 reporting 비용 문서에 반영됨

## Plan Quality Audit

현재 계획은 아래 기준을 충족해야 90점 이상으로 본다.

| 항목 | 기준 | 현재 상태 |
| --- | --- | --- |
| 범위 명확성 | MVP 기본 산출물과 확장 산출물이 분리됨 | 충족 |
| 데이터 입력 경계 | S3 processed 우선, raw 직접 LLM 입력 제외 | 충족 |
| smoothing 방지 | 평균 외 spike/worst/evidence 보존 | 충족 |
| hour 경계 처리 | 인접 hour 이벤트 병합 기준 존재 | 충족 |
| 이벤트 우선순위 | severity_score와 top N 정책 존재 | 충족 |
| factory별 해석 | production/testbed interpretation mode 존재 | 충족 |
| 추적성 | message_id/S3 key evidence 보존 | 충족 |
| LLM 안전성 | Bedrock 출력 invariant 검증 기준과 pipeline 단계 존재 | 충족 |
| 확장 산출물 | DOCX/PDF는 후처리 Lambda 확장으로 분리 | 충족 |
| 구현 착수성 | 앱/인프라 위치와 테스트 순서 제시 | 충족 |

남은 항목은 구현 전 검증값이며, 현재 계획의 구조적 완성도를 막지는 않는다.

## 확정 기본값과 변경 필요 항목

아래 값은 MVP 구현 기본값으로 확정한다. 구현 중 변경이 필요하면 사용자 승인 후 이 문서를 먼저 수정한다.

| 항목 | 확정 기본값 |
| --- | --- |
| AWS region | `ap-south-1` |
| Bedrock 모델 ID | `anthropic.claude-3-haiku-20240307-v1:0` |
| 보고서 언어 | 한국어 |
| 생성 시각 | 매일 00:30 KST |
| late arrival 대기 | 30분 |
| threshold source | reporting Lambda 환경변수 기본값. 후속으로 `runtime-config.yaml` 연동 가능 |
| severity_score 기준 | 이 문서의 `Severity Score` 초기 점수 기준 |
| event top N | `MAX_CONTEXT_EVENTS=10` |
| recommended checks | `MAX_RECOMMENDED_CHECKS=5` |
| hour 경계 이벤트 병합 gap | `EVENT_MERGE_GAP_SECONDS=120` |
| report-context 최대 크기 | `MAX_CONTEXT_BYTES=120000` |
| intermediate hourly summary 보존 | MVP에서는 삭제하지 않음. lifecycle은 후속 운영 정책에서 결정 |
| `bedrock-response.json` 저장 | 기본 `false` |
| DOCX/PDF | 확장 범위. MVP 기본 출력은 Markdown |
| 전체 공장 요약 보고서 | 후속 확장 범위 |
| reporting Terraform의 S3 참조 방식 | `data_bucket_name` variable + `data.aws_s3_bucket` 조회 |

구현 전 다시 확인할 항목은 아래뿐이다.

- 실제 AWS 계정의 `ap-south-1` region에서 선택한 Bedrock model 사용 권한이 열려 있는지
- `aegis-bucket-data` bucket 이름이 대상 환경에서 동일한지. 다르면 `data_bucket_name` variable로 override한다.

## 다음 세션 시작 상태

2026-05-27 세션 최신 기준 상태다. 다음 세션에서 사용자가 "`17_llm_daily_factory_report_plan.md` 파일 확인하고 바로 보고서 생성 파이프라인 진행하자"고 요청하면, 이 섹션을 확인한 뒤 별도 설계 재논의 없이 구현을 이어간다.

현재 완료 상태:

- `factory-a/b/c` data-pipeline은 실제 AWS 리소스 기준 end-to-end 검증 완료.
- Region은 `ap-south-1`로 확정.
- S3 bucket은 `aegis-bucket-data`를 기본값으로 사용.
- IoT Core Rule 3개는 S3 raw action과 Lambda action을 통해 data processor로 연결됨.
- `AEGIS-Lambda-DataProcessor`는 Active/Successful 상태로 검증됨.
- DynamoDB `AEGIS-DynamoDB-FactoryStatus`는 `factory-a/b/c` LATEST 갱신 확인.
- S3 `processed/factory-a,b,c/`에 `factory_state`, `risk_score`, `infra_state`, `state_snapshot` 적재 확인.
- 최신 `factory-a` processed `state_snapshot` 기준 `nodes_ready=3/3`, `pods_ready=6/6`, `pipeline_status=normal`.
- `factory-a` infra metrics는 최신 포맷 기준으로 채워짐:
  - `node_id`
  - `ready`
  - `cpu_usage_percent`
  - `memory_usage_percent`
  - `disk_usage_percent`
  - `network_reachability`
  - device `available`
- `factory-b/c`는 테스트베드형 factory이며 dummy data generator + common publisher 기반이다.
- LLM daily report는 MVP 포함으로 확정.
- Bedrock에는 S3 raw 원본 전체를 직접 넣지 않고, Lambda가 만든 `report-context.json`만 전달한다.
- `infra/reporting/`은 foundation remote state를 읽지 않고 `data_bucket_name` variable + `data.aws_s3_bucket` 조회 방식으로 구현한다.
- `apps/daily-report-generator/` skeleton과 핵심 로컬 로직 구현을 진행했다.
- `AggregateFactoryHour`는 `not_ready_nodes`, `unhealthy_workloads`를 infra summary에 구조화하고, node 이름이 비어 있으면 `control-plane:Unknown`, `worker:Unknown`처럼 추적 가능한 fallback label을 사용한다.
- `MergeFactoryDaily`는 `ai_spike_event_count`, `ai_spike_event_examples`, `likely_infra_causes`, rule 기반 `recommended_checks`를 context에 포함한다.
- `recommended_checks`는 risk degradation, sensor threshold, AI spike, abnormal sound, node readiness, unhealthy workload, data gap, restart 조건을 기준으로 priority/reason/evidence message id를 구성한다.
- `PromptBuilder`는 AI spike evidence, infra cause, recommended checks, S3 processed/raw 한계, testbed/dummy 해석, LLM 초안 검토 필요를 보고서에 반영하도록 갱신했다.
- `factory-b` `hh=03` enriched v2 테스트 context/prompt/hourly summary와 검토 노트를 `/home/vicbear/Aegis/test_paper/`에 저장했다.
- enriched v2 Bedrock 실호출과 AWS 배포는 아직 수행하지 않았다.

이미 최신화한 문서:

- `docs/product/00_mvp_scope.md`
- `docs/product/02_requirements_definition.md`
- `docs/planning/00_project_overview.md`
- `docs/planning/02_implementation_plan.md`
- `docs/ops/15_aws_cost_baseline.md`
- `docs/ops/24_daily_factory_report.md`
- `docs/specs/data_storage_pipeline.md`
- `apps/data-processor/README.md`
- `docs/issues/SESSION_STATE.md`
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-enriched-v2-test-note.md`
- `/home/vicbear/Aegis/0527-daily-report-session.md`

검증 상태:

- `python -m pytest -q`: 통과, 9 passed.
- `python -m compileall -q apps/daily-report-generator`: 통과.
- `terraform fmt -check -diff`: 통과.
- `terraform validate`: sandbox provider plugin 실행 제한으로 실패했고, escalated 재시도는 사용량 제한으로 거절되어 이번 세션에서 재검증하지 못했다. 이전 validate/plan은 통과했던 상태로 기록되어 있다.
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-report-context-enriched-v2.json`은 단일 `hh=03` 파티션 기반 테스트 context이므로 `missing_hour_count=23`이 정상이다. 24시간 전체 daily merge에서 `missing_hour_count=0`인지 별도 검증이 필요하다.

다음 세션에서 바로 시작할 작업:

1. `git_clone/Aegis-pi` 기준으로 변경 파일 상태를 확인한다.
2. `terraform validate`를 AWS/provider plugin 실행이 가능한 환경에서 재실행한다.
3. enriched v2 context로 Bedrock 실호출을 수행하고 `factory-b-hh03-report.md` 또는 별도 v2 report 파일을 생성한다.
4. 생성된 Markdown에서 factory/date/Risk Score/collection count/evidence id/recommended checks/S3 processed 한계가 context와 일치하는지 검증한다.
5. 단일 hour 테스트와 별도로 24시간 daily merge fixture 또는 실제 processed day 입력으로 `missing_hour_count=0`, 24시간 count 합산, hour boundary event merge를 검증한다.
6. `infra/reporting/`, `build-reporting.sh`, `destroy-reporting.sh`를 배포 전 기준으로 한 번 더 검토한다.
7. AWS 배포 후 Step Functions reporting pipeline 수동 실행으로 S3 `reports/daily/` 산출물 저장까지 검증한다.

구현 시작 전 실무 확인:

- `ap-south-1`에서 `anthropic.claude-3-haiku-20240307-v1:0` model access가 열려 있는지 확인.
- 만약 해당 모델이 `ap-south-1`에서 사용 불가하면, 같은 문서의 Bedrock model ID 기본값을 사용자 승인 후 변경한다.

## 다음 세션 작업 지시

새 세션에서 바로 구현을 시작하려면 아래 순서로 진행한다.

1. 이 문서와 `docs/ops/24_daily_factory_report.md`를 읽는다.
2. 현재 결정값이 유지되는지 확인한다. 사용자가 바로 진행하라고 하면 확인 질문 없이 구현한다.
3. 로컬 테스트를 먼저 재실행한다.
4. `terraform validate`를 재검증한다.
5. enriched v2 Bedrock 실호출을 수행한다.
6. Bedrock 출력 invariant와 문서 품질을 검토한다.
7. 24시간 daily merge 검증을 추가한다.
8. 검증이 끝나면 reporting stack을 배포하고 Step Functions 수동 실행으로 S3 산출물을 확인한다.
9. 비용 기준 문서는 이미 기본 추정이 반영되어 있으므로, 실제 리소스 배포 후 단가/사용량이 달라지면 갱신한다.

## 2026-05-28 검증 결과

이 섹션이 위의 2026-05-27 handoff 문구보다 최신이다.

검증 완료:

- `python -m compileall -q apps/daily-report-generator` 통과.
- `python -m pytest -q apps/daily-report-generator` 통과, 10 passed.
- `terraform -chdir=infra/reporting fmt -check -diff` 통과.
- `terraform -chdir=infra/reporting init` 통과.
- `terraform -chdir=infra/reporting validate` 통과.
- `scripts/build/build-reporting.sh` 실행 완료, Terraform apply 결과 17 added.
- Terraform output 확인:
  - `state_machine_name=AEGIS-DailyFactoryReportStateMachine`
  - `state_machine_arn=arn:aws:states:ap-south-1:611058323802:stateMachine:AEGIS-DailyFactoryReportStateMachine`
  - `scheduler_name=AEGIS-Schedule-DailyFactoryReport`
  - `data_bucket_name=aegis-bucket-data`
- Step Functions 수동 실행 완료:
  - execution name: `manual-factory-report-20260528T012107Z`
  - status: `SUCCEEDED`
  - input: `report_date=2026-05-27`, `timezone=Asia/Seoul`, `factories=["factory-b"]`, `report_type=daily_factory_operations_draft`
- S3 output 확인:
  - `s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=05/dd=27/factory-b/`
  - `intermediate/hourly/hh=00.json`~`hh=23.json`
  - `factory-daily-summary.json`
  - `report-context.json`
  - `report.md`
  - `generation-metadata.json`
- `report-context.json` 확인:
  - KST report window: `2026-05-27T00:00:00+09:00`~`2026-05-27T23:59:59+09:00`
  - UTC S3 query window: `2026-05-26T15:00:00Z`~`2026-05-27T14:59:59Z`
  - `s3_partition_timezone=UTC`
  - `data_limitations`에 S3 processed 기반/raw 미사용/testbed dummy 해석 포함
- `generation-metadata.json` 확인:
  - `model_id=anthropic.claude-3-sonnet-20240229-v1:0`
- `report.md` 확인:
  - 사용자 친화적 용어 사용
  - 검증 기준 수치 섹션에 원문 field 유지
  - 결측 구간을 `top_gap_window`와 분 단위 `duration_minutes`로 표현
  - S3 processed 기반, S3 raw 미사용, factory-b/c testbed dummy 해석 명시

검증 후 운영 상태:

- 자동 실행 비용 방지를 위해 `scripts/destroy/destroy-reporting.sh`를 실행했다.
- Terraform destroy 결과 17 destroyed.
- 삭제 대상은 Scheduler, Step Functions, reporting Lambda 4개, 관련 IAM role/policy, CloudWatch LogGroup이다.
- S3 `processed/` 입력과 `reports/daily/` 산출물은 삭제하지 않고 보존한다.

비용/성능 관찰:

- 기준 실행의 입력 object 수는 약 65,050개였다.
- `state_snapshot`만 약 27,915개였고, 일부 hour에서 `AggregateFactoryHour`가 수분 단위로 실행됐다.
- 병목은 report output 크기가 아니라 작은 S3 processed object 다량 순차 `GetObject`다.
- 현재 1회 factory report 비용은 Free Tier 제외 기준 약 `0.12~0.18 USD`로 추정한다.
- 상세 비용 기준은 `docs/ops/25_daily_factory_report_cost.md`에 둔다.

후속 고도화:

1. `S3ProcessedReader`가 `S3_GET_CONCURRENCY`를 실제로 사용하도록 병렬 `GetObject`를 구현한다.
2. `state_snapshot` 전체를 읽지 않고 latest N개 또는 hour별 마지막 snapshot만 읽도록 줄인다.
3. `generation-metadata.json`에 Bedrock token usage, input context bytes, output bytes, input object count를 저장한다.
4. reporting stack은 필요할 때만 `scripts/build/build-reporting.sh`로 다시 올리고, 검증/실행 후 `scripts/destroy/destroy-reporting.sh`로 내린다.
