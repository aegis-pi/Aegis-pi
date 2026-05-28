# Daily Factory Report Cost Estimate

상태: cost baseline
기준일: 2026-05-28

## 목적

이 문서는 Daily Factory Report 1회 생성 비용을 추정하는 기준을 정리한다.

기준 실행은 `factory-b`, `report_date=2026-05-27`, `timezone=Asia/Seoul`, `report_type=daily_factory_operations_draft` 수동 Step Functions 실행이다.

```text
execution_name: manual-factory-report-20260528T012107Z
execution_status: SUCCEEDED
execution_time: 2026-05-28 10:21:08~10:30:31 KST
output_prefix: s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=05/dd=27/factory-b/
```

비용은 AWS Free Tier 적용 전후에 달라질 수 있다. 아래 표는 Free Tier를 제외한 marginal cost 기준의 근사값이다.

## 현재 처리 구조

Reporting stack은 S3 `processed/` object를 읽어 hour 단위 summary를 만들고, 24개 hourly summary를 병합한 뒤 Bedrock으로 Markdown 초안을 생성한다.

```text
EventBridge Scheduler
  -> Step Functions Standard Workflow
      -> PrepareReportWindow Lambda
      -> 24 x AggregateFactoryHour Lambda
      -> MergeFactoryDaily Lambda
      -> GenerateFactoryReport Lambda
          -> Bedrock Claude 3 Sonnet
```

현재 배포 구성은 기본 dataset에 더해 보조 dataset `state_snapshot`도 읽는다.

```text
REPORT_DATASETS=factory_state,risk_score,infra_state
REPORT_AUX_DATASETS=state_snapshot
```

중요한 병목은 산출물 크기가 아니라 S3 입력 object 수다. `report.md`와 `report-context.json`은 작지만, 입력 `processed/` object가 잘게 쪼개져 있어 Lambda가 많은 `GetObject` 요청을 수행한다.

## 기준 실행 입력 규모

`report-context.json`과 S3 prefix 확인 기준:

| Dataset | 입력 object/record 수 |
| --- | ---: |
| `factory_state` | 17,272 |
| `risk_score` | 17,272 |
| `infra_state` | 2,591 |
| `state_snapshot` | 27,915 |
| 합계 | 65,050 |

대표적으로 데이터가 많았던 KST 15시 hour는 아래 규모였다.

| Dataset | KST 15시 입력 수 |
| --- | ---: |
| `factory_state` | 1,199 |
| `risk_score` | 1,199 |
| `infra_state` | 180 |
| `state_snapshot` | 2,614 |
| 합계 | 5,192 |

이 hour 하나의 `AggregateFactoryHour` Lambda는 약 4분 52초가 걸렸다. 이는 큰 파일을 다운로드해서가 아니라 작은 JSON object 수천 개를 순차 `GetObject`로 읽기 때문이다.

## Lambda 비용

CloudWatch `REPORT` line 기준 billed duration:

| Lambda | 호출 수 | 메모리 | Billed duration |
| --- | ---: | ---: | ---: |
| `AggregateFactoryHour` | 24 | 1024 MB | 약 2,630.9초 |
| `PrepareReportWindow` | 1 | 512 MB | 약 0.1초 |
| `MergeFactoryDaily` | 1 | 512 MB | 약 2.5초 |
| `GenerateFactoryReport` | 1 | 512 MB | 약 33.4초 |

GB-second 환산:

```text
AggregateFactoryHour: 2,630.9 sec * 1.0 GB = 2,630.9 GB-sec
PrepareReportWindow: 0.1 sec * 0.5 GB = 0.05 GB-sec
MergeFactoryDaily: 2.5 sec * 0.5 GB = 1.25 GB-sec
GenerateFactoryReport: 33.4 sec * 0.5 GB = 16.7 GB-sec
total: 약 2,648.9 GB-sec
```

AWS Lambda x86 on-demand 단가를 `0.0000166667 USD/GB-sec`, request 단가를 `0.20 USD / 1M requests`로 두면:

```text
compute: 2,648.9 * 0.0000166667 ~= 0.0441 USD
requests: 27 / 1,000,000 * 0.20 ~= 0.00001 USD
```

Lambda 비용은 1회 약 `0.044 USD`로 본다.

## S3 비용

현재 reader는 각 input object마다 `GetObject`를 호출한다. 기준 실행에서는 입력 object만 약 65,050개였다.

S3 Standard GET 단가를 `0.0004 USD / 1,000 requests`로 두면:

```text
GET: 65,050 / 1,000 * 0.0004 ~= 0.0260 USD
```

LIST/PUT 요청은 GET에 비해 작다.

```text
LIST: hour 24개 * dataset 4개 = 약 96 requests
PUT: hourly summary 24개 + daily/context/report/metadata = 약 28 requests
```

LIST는 PUT/COPY/POST 계열 요청 단가로 과금되지만 이 규모에서는 `0.001 USD` 미만이다.

S3 data transfer는 같은 region 내 Lambda -> S3 access 기준으로 별도 인터넷 egress 비용으로 보지 않는다. S3 storage 증분도 report output이 수십 KB 수준이므로 1회 비용에서는 무시 가능하다.

S3 비용은 1회 약 `0.026~0.027 USD`로 본다.

## Step Functions 비용

State machine은 Standard Workflow다. Standard Workflow는 state transition 기준으로 과금된다.

이번 실행은 factory 1개, hour 24개 Map branch 기준이며 retry 없이 성공했다. 실제 transition 수는 definition과 Map iteration에 따라 달라지지만 1회당 약 100~150 transitions 범위로 보는 것이 보수적이다.

단가를 `0.000025 USD / transition`으로 두면:

```text
100 transitions * 0.000025 = 0.0025 USD
150 transitions * 0.000025 = 0.00375 USD
```

Step Functions 비용은 1회 약 `0.003~0.004 USD`로 본다.

## Bedrock 비용

`GenerateFactoryReport`는 Bedrock Claude 3 Sonnet을 1회 호출한다.

```text
model_id=anthropic.claude-3-sonnet-20240229-v1:0
```

현재 `generation-metadata.json`에는 token usage가 저장되지 않는다. 따라서 비용은 prompt 크기와 report 출력 길이 기준 추정이다.

기준 실행 파일 크기:

| Artifact | Size |
| --- | ---: |
| `report-context.json` | 14,473 bytes |
| `report.md` | 5,728 bytes |
| `generation-metadata.json` | 252 bytes |

Prompt에는 `report-context.json` 외에도 한국어 지시문이 포함된다. 따라서 보수적으로 input 8k~15k tokens, output 2k~3k tokens로 추정한다.

Claude 3 Sonnet 계열을 input `3 USD / 1M tokens`, output `15 USD / 1M tokens` 수준으로 두면:

```text
input: 8k~15k * 3 / 1,000,000 = 0.024~0.045 USD
output: 2k~3k * 15 / 1,000,000 = 0.030~0.045 USD
total: 0.054~0.090 USD
```

Bedrock 비용은 1회 약 `0.05~0.09 USD`로 본다.

정확한 비용 추적이 필요하면 Bedrock response header 또는 response body의 token usage를 `generation-metadata.json`에 저장하도록 구현을 보강한다.

## CloudWatch Logs와 Scheduler 비용

CloudWatch Logs는 Lambda `REPORT` line과 소량의 application log만 남는다. 1회 실행의 log ingest는 수십 KB 수준이므로 비용은 `0.001 USD` 미만으로 본다.

EventBridge Scheduler는 월 14M invocations free tier가 있어 이 프로젝트의 daily schedule 규모에서는 보통 별도 비용을 무시할 수 있다. Free Tier를 제외해도 1일 1회 invocation 비용은 사실상 무시 가능하다.

## 1회 비용 합계

| 항목 | 1회 비용 추정 |
| --- | ---: |
| Lambda compute/request | 약 `0.044 USD` |
| S3 GET/LIST/PUT | 약 `0.026~0.027 USD` |
| Step Functions | 약 `0.003~0.004 USD` |
| Bedrock Claude 3 Sonnet | 약 `0.05~0.09 USD` |
| CloudWatch Logs/Scheduler | 약 `0.001 USD` 미만 |
| 합계 | 약 `0.12~0.18 USD` |

따라서 현재 factory-b 기준 일일 리포트 1개 생성 비용은 Free Tier 제외 기준 약 `0.12~0.18 USD`로 잡는다.

## 월간 비용 추정

`factory-a/b/c` 3개 공장을 매일 1회 생성하고, factory별 데이터량이 factory-b와 비슷하다고 가정하면:

```text
daily: 0.12~0.18 USD * 3 factories = 0.36~0.54 USD/day
monthly: 0.36~0.54 USD/day * 30 days = 10.8~16.2 USD/month
```

실제 비용은 factory별 입력 object 수와 Bedrock 출력 길이에 따라 달라진다.

## 비용 민감도

비용을 좌우하는 항목은 아래 순서다.

1. Bedrock output tokens
2. Lambda billed duration
3. S3 `GetObject` request count
4. Step Functions state transitions

현재 구조에서는 Lambda billed duration과 S3 GET 수가 같은 원인에서 증가한다. processed object가 작은 JSON 파일로 많이 쪼개져 있고, `S3ProcessedReader`가 순차 `GetObject`를 수행하기 때문이다.

## 비용 절감 후보

우선순위:

1. `S3ProcessedReader`에서 `GetObject` 병렬화
   - `S3_GET_CONCURRENCY=16` 환경변수는 이미 있지만 현재 reader 구현은 이를 사용하지 않는다.
   - wall-clock duration과 Lambda billed duration을 줄일 수 있다.

2. `state_snapshot` 입력 축소
   - 기준 실행에서 `state_snapshot`만 27,915 objects였다.
   - report에 필요한 값은 최종 snapshot과 일부 상태 요약이므로 latest N개 또는 hour별 마지막 object만 읽어도 충분할 수 있다.

3. processed compact object 생성
   - data processor 또는 별도 compaction job이 minute/hour 단위 compact JSONL을 만들고, reporting은 compact file만 읽는다.
   - S3 GET 수와 Lambda duration을 가장 구조적으로 줄일 수 있다.

4. Bedrock token usage 저장
   - `generation-metadata.json`에 input/output token count를 남기면 비용을 추정이 아니라 실측으로 관리할 수 있다.

5. Step Functions concurrency 조정
   - `HourMap MaxConcurrency`를 높이면 wall-clock은 줄 수 있지만 S3 request burst와 Lambda 동시성은 증가한다.
   - 현재 병목은 Lambda 내부 순차 I/O이므로 concurrency 조정은 보조 수단이다.

## 운영 기준

- 일일 자동 실행을 유지할 경우 `factory-a/b/c` 전체 월 비용은 우선 `10~20 USD/month` 범위로 예산을 잡는다.
- 월 비용이 이 범위를 벗어나면 먼저 S3 GET count, Lambda GB-sec, Bedrock output tokens를 확인한다.
- 리포트 생성 속도가 문제이면 `state_snapshot` 축소 또는 S3 compact object가 우선이다.
- 비용 정밀 추적이 필요해지면 `generation-metadata.json`에 Bedrock token usage와 S3 input object count를 저장한다.

## 참고 가격 문서

- AWS Lambda pricing: https://aws.amazon.com/lambda/pricing/
- Amazon S3 pricing: https://aws.amazon.com/s3/pricing/
- AWS Step Functions pricing: https://aws.amazon.com/step-functions/pricing/
- Amazon Bedrock pricing: https://aws.amazon.com/bedrock/pricing/
- Amazon EventBridge Scheduler: https://aws.amazon.com/eventbridge/scheduler/
