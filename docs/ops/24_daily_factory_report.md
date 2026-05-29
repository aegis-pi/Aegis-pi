# Daily Factory Report

상태: validated runbook
기준일: 2026-05-28

## 목적

이 문서는 Bedrock 기반 factory별 일일 운영 보고서 생성 기능의 운영 기준을 정리한다.

설계 source of truth는 `docs/planning/17_llm_daily_factory_report_plan.md`다. 이 문서는 배포, 점검, 장애 대응 시 운영자가 확인할 기준만 둔다.

2026-05-28 기준 구현은 로컬 검증, Bedrock Sonnet 실호출, AWS 배포, Step Functions 수동 실행까지 완료됐다. `factory-b`, `report_date=2026-05-27`, `timezone=Asia/Seoul` 최종 실행 `manual-factory-report-20260528T064840Z`는 `SUCCEEDED`였고, S3 `reports/daily/yyyy=2026/mm=05/dd=27/factory-b/` 산출물을 확인했다. 검증 중 Bedrock 출력 heading trailing space 때문에 `인프라 상태` 표가 삽입되지 않는 케이스를 수정했고, 최종 `report.md`에서 핵심 지표/데이터 수집/Risk Score/센서 및 AI 이벤트/인프라 상태/주요 이벤트/확인 필요 항목 표와 분석 문단을 확인했다. 검증 후 reporting stack은 비용 방지를 위해 삭제했으며, S3 `processed/` 입력과 `reports/daily/` 산출물은 보존한다.

## 범위

MVP 포함 범위:

- `factory-a`, `factory-b`, `factory-c` 개별 일일 보고서
- 전일 KST 00:00:00~23:59:59 대상
- 매일 00:30 KST 실행
- S3 `processed/` 입력 기반 집계
- Bedrock 기반 한국어 Markdown 초안 생성
- S3 `reports/daily/` 산출물 저장

MVP 제외 범위:

- S3 `raw/` 원본 전체를 Bedrock에 직접 전달
- 전체 공장 통합 보고서
- DOCX/PDF 자동 생성
- 보고서 기반 자동 재학습 또는 자동 배포

## AWS Region

```text
ap-south-1
```

배포 전 `ap-south-1`에서 선택한 Bedrock model access가 열려 있는지 확인한다.

## 입력과 출력

보고서 기준일은 운영자 기준인 KST 하루다. S3 processed partition은 UTC 기준을 유지한다.

예를 들어 `report_date=2026-05-27`, `timezone=Asia/Seoul`이면 보고서 기준과 S3 조회 범위는 아래처럼 달라진다.

```text
보고서 기준: 2026-05-27 KST 00:00:00~23:59:59
S3 조회 범위: 2026-05-26T15:00:00Z~2026-05-27T14:59:59Z
```

`PrepareReportWindow`가 KST 기준 hour window와 UTC 조회 window를 함께 만들고, `S3ProcessedReader`가 UTC partition prefix를 계산한다. Hour boundary는 `start <= timestamp < next_hour` 기준으로 처리해 `23:59:59.xxx` 같은 millisecond timestamp가 누락되지 않게 한다.

입력 prefix:

```text
processed/{factory_id}/factory_state/yyyy=YYYY/mm=MM/dd=DD/hh=HH/
processed/{factory_id}/risk_score/yyyy=YYYY/mm=MM/dd=DD/hh=HH/
processed/{factory_id}/infra_state/yyyy=YYYY/mm=MM/dd=DD/hh=HH/
```

출력 prefix:

```text
reports/daily/yyyy=YYYY/mm=MM/dd=DD/{factory_id}/
  intermediate/hourly/hh=00.json
  ...
  intermediate/hourly/hh=23.json
  factory-daily-summary.json
  report-context.json
  report.md
  generation-metadata.json
```

`state_snapshot/`은 현재 보조 입력으로 함께 읽는다. 다만 기준 실행에서 `state_snapshot` object 수가 많아 비용/성능 병목이 확인됐으므로, 후속 고도화에서는 latest N개 또는 hour별 마지막 snapshot만 읽도록 줄이는 것을 우선 검토한다.

## 구성 요소

```text
EventBridge Scheduler
  -> Step Functions: DailyFactoryReportStateMachine
      -> PrepareReportWindow
      -> AggregateFactoryHour
      -> MergeFactoryDaily
      -> GenerateFactoryReport
```

Lambda 역할:

| Lambda | 역할 |
| --- | --- |
| `PrepareReportWindow` | KST report date/window, factory 목록, output prefix 계산 |
| `AggregateFactoryHour` | factory/hour 단위 S3 processed 집계 |
| `MergeFactoryDaily` | 24개 hourly summary 병합, report-context 생성 |
| `GenerateFactoryReport` | Bedrock 호출, invariant validation, Markdown 저장 |

## Terraform 기준

Reporting stack은 별도 root module로 둔다.

```text
infra/reporting/
```

S3 bucket 참조 방식:

```text
data_bucket_name variable + data.aws_s3_bucket lookup
```

MVP에서는 foundation remote state를 읽지 않는다. Reporting stack이 필요한 foundation 출력은 현재 S3 bucket name/ARN뿐이며, bucket 생성/삭제 소유권은 foundation에 남긴다.

비용 산정 기준은 `docs/ops/25_daily_factory_report_cost.md`를 따른다.

현재 reporting stack은 검증 후 삭제된 상태다. 필요할 때만 `scripts/build/build-reporting.sh [MFA_OTP]`로 올리고, 검증 또는 수동 실행 후 `scripts/destroy/destroy-reporting.sh [MFA_OTP]`로 내린다.

## 운영 점검

배포 후 일일 점검 항목:

- EventBridge Scheduler가 00:30 KST에 Step Functions execution을 시작했는지 확인
- Step Functions Map branch에서 `factory-a/b/c`가 독립적으로 완료됐는지 확인
- 각 factory output prefix에 `report-context.json`, `factory-daily-summary.json`, `report.md`, `generation-metadata.json`이 있는지 확인
- `generation-metadata.json`의 validation status가 success인지 확인
- CloudWatch Logs에 Bedrock throttling, S3 AccessDenied, schema validation error가 없는지 확인

인프라 상태 확인은 현재 S3 `processed/infra_state`와 `state_snapshot` 입력을 기준으로 보고서에 반영한다. 후속 확장에서는 CloudWatch를 보조 관측원으로 추가해, 보고서 생성 후 운영자가 Lambda/Step Functions 실행 상태와 실제 AWS 인프라 신호를 함께 확인할 수 있게 한다.

CloudWatch 확장 방향:

- Lambda log group과 Step Functions execution log에서 reporting 파이프라인 자체의 오류, timeout, retry, billed duration을 조회한다.
- factory별 인프라 판단은 S3 processed 데이터가 primary source이고, CloudWatch는 AWS 리소스 실행/장애 근거를 보강하는 secondary source로 둔다.
- `report-context.json`에는 CloudWatch 조회 window, 조회한 log group/metric namespace, 발견된 오류 카운트 같은 요약 필드만 넣고 raw log line 전문은 넣지 않는다.
- `report.md`의 인프라 상태 섹션에는 processed 기반 노드/워크로드 상태와 CloudWatch 기반 Lambda/Step Functions 상태를 구분해서 표시한다.
- CloudWatch 권한을 추가할 때는 reporting Lambda role에 필요한 `logs:FilterLogEvents`, `logs:StartQuery`, `logs:GetQueryResults`, `cloudwatch:GetMetricData` 범위를 최소 log group/metric namespace로 제한한다.
- destroy 기준은 유지한다. reporting stack destroy는 reporting Lambda, Step Functions, Scheduler, 관련 IAM/LogGroup만 삭제하고 S3 `processed/`와 `reports/daily/` 객체는 보존한다.

S3 확인 예시:

```bash
aws s3 ls s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=05/dd=27/factory-a/ --region ap-south-1
```

## 실패 대응

| 증상 | 확인 |
| --- | --- |
| 특정 factory만 실패 | Step Functions Map branch result와 해당 factory Lambda log 확인 |
| `report-context.json`은 있으나 `report.md` 없음 | Bedrock 호출 실패 또는 output invariant validation 실패 확인 |
| hourly summary 일부가 empty | 해당 시간대 S3 processed prefix와 collection rate 확인 |
| 전체 실행 시작 안 됨 | EventBridge Scheduler state, IAM `states:StartExecution` 권한 확인 |
| S3 AccessDenied | reporting Lambda role의 `processed/` read와 `reports/daily/` write policy 확인 |
| Bedrock AccessDenied | `ap-south-1` model access와 IAM `bedrock:InvokeModel` 또는 Converse 권한 확인 |

## 안전 기준

- Bedrock 출력은 운영 판단의 정본이 아니라 운영자 검토용 초안이다.
- Lambda가 계산한 수치, 날짜, factory ID를 Bedrock이 바꾸면 저장 전 validation 실패로 처리한다.
- 로그에 raw payload, Bedrock prompt 전문, secret, token, certificate 원문을 남기지 않는다.
- `factory-b/c`는 테스트베드형 공장이므로 보고서 문구에서 실제 현장 장애로 단정하지 않는다.

## 후속 검증

- factory-a/c도 실제 운영 기준인 KST 하루치 입력으로 end-to-end 실행을 검증한다.
- KST day boundary에서 `23:59:59.xxx` timestamp가 해당 날짜에 포함되고, 다음 날짜 `00:00:00.000` 이후 데이터가 섞이지 않는지 주기적으로 확인한다.
- `S3ProcessedReader`의 순차 `GetObject` 병목을 줄이기 위해 `S3_GET_CONCURRENCY` 병렬화를 구현한다.
- `generation-metadata.json`에 Bedrock token usage, context bytes, output bytes, input object count를 남긴다.
- CloudWatch Logs/metrics 기반 인프라 상태 보조 조회를 추가해 reporting 파이프라인 상태와 factory 인프라 판단 근거를 같은 보고서에서 분리 표시한다.
