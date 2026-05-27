# Daily Factory Report

상태: implementation runbook
기준일: 2026-05-27

## 목적

이 문서는 Bedrock 기반 factory별 일일 운영 보고서 생성 기능의 운영 기준을 정리한다.

설계 source of truth는 `docs/planning/17_llm_daily_factory_report_plan.md`다. 이 문서는 배포, 점검, 장애 대응 시 운영자가 확인할 기준만 둔다.

2026-05-27 기준 구현은 로컬 검증까지 진행됐다. `apps/daily-report-generator/`와 `infra/reporting/`은 생성됐고, pytest/compileall/terraform fmt는 통과했다. `terraform validate`, enriched v2 Bedrock 실호출, 24시간 daily merge 검증, AWS 배포는 다음 작업이다.

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

`state_snapshot/`은 기본 입력이 아니다. 기본 dataset만으로 보고서 필드가 부족할 때 제한적으로 보조 입력으로 검토한다.

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

## 운영 점검

배포 후 일일 점검 항목:

- EventBridge Scheduler가 00:30 KST에 Step Functions execution을 시작했는지 확인
- Step Functions Map branch에서 `factory-a/b/c`가 독립적으로 완료됐는지 확인
- 각 factory output prefix에 `report-context.json`, `factory-daily-summary.json`, `report.md`, `generation-metadata.json`이 있는지 확인
- `generation-metadata.json`의 validation status가 success인지 확인
- CloudWatch Logs에 Bedrock throttling, S3 AccessDenied, schema validation error가 없는지 확인

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
