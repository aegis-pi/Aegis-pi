# 2026-05-27 Daily Factory Report Session

상태: completed handoff
기준일: 2026-05-28

## 목적

Bedrock 기반 daily factory report 작업의 구현/검증 결과를 저장하는 문서다. 공식 진행 스냅샷은 `docs/issues/SESSION_STATE.md`를 우선한다.

## 현재 완료

- `apps/daily-report-generator/` package와 4개 Lambda handler 구현을 진행했다.
- `AggregateFactoryHour`는 infra summary에 `not_ready_nodes`, `unhealthy_workloads`를 구조화한다.
- node 이름이 비어 있으면 `control-plane:Unknown`, `worker:Unknown` 같은 fallback label을 사용한다.
- `MergeFactoryDaily`는 AI spike count/examples, likely infra causes, recommended checks를 context에 포함한다.
- `recommended_checks`는 rule 기반으로 priority/reason/evidence message id를 구성한다.
- `PromptBuilder`는 AI spike evidence, infra cause, recommended checks, S3 processed/raw 한계, testbed/dummy 해석을 보고서에 반영한다.
- `infra/reporting/` Terraform root module과 `build-reporting.sh`, `destroy-reporting.sh`를 추가했다.
- Bedrock Sonnet 실호출, 24시간 `factory-b` Step Functions 수동 실행, S3 산출물 검증을 완료했다.
- 비용 산정 기준 문서 `docs/ops/25_daily_factory_report_cost.md`를 추가했다.
- 검증 후 reporting stack은 `destroy-reporting.sh`로 삭제했고 S3 `processed/` 입력과 `reports/daily/` 산출물은 보존했다.

## 테스트 산출물

- `/home/vicbear/Aegis/test_paper/factory-b-hh03-report-context-enriched-v2.json`
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-prompt-enriched-v2.txt`
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-hourly-aggregate-enriched-v2.json`
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-enriched-v2-test-note.md`

## 검증 상태

- `python -m pytest -q apps/daily-report-generator`: 통과, 10 passed.
- `python -m compileall -q apps/daily-report-generator`: 통과.
- `terraform -chdir=infra/reporting fmt -check -diff`: 통과.
- `terraform -chdir=infra/reporting init`: 통과.
- `terraform -chdir=infra/reporting validate`: 통과.
- `scripts/build/build-reporting.sh`: apply 완료, 17 added.
- Step Functions 수동 실행: `manual-factory-report-20260528T012107Z`, `SUCCEEDED`.
- S3 output: `s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=05/dd=27/factory-b/`.
- 확인 산출물: `intermediate/hourly/hh=00.json`~`hh=23.json`, `factory-daily-summary.json`, `report-context.json`, `report.md`, `generation-metadata.json`.
- `report-context.json`의 report window: KST `2026-05-27T00:00:00+09:00`~`23:59:59+09:00`, UTC `2026-05-26T15:00:00Z`~`2026-05-27T14:59:59Z`.
- `generation-metadata.json`의 `model_id`: `anthropic.claude-3-sonnet-20240229-v1:0`.
- `scripts/destroy/destroy-reporting.sh`: destroy 완료, 17 destroyed.

## 남은 작업

1. Daily Report S3 read 성능 개선: `S3_GET_CONCURRENCY` 실제 적용, `state_snapshot` 읽기 축소.
2. `generation-metadata.json`에 Bedrock token usage, context bytes, output bytes, input object count 저장.
3. 필요 시 reporting stack을 `scripts/build/build-reporting.sh`로 다시 올리고 수동/자동 실행 검증.
4. 이후 M6 `runtime-config.yaml` 적용, Risk Twin 출력 구조 구현 진행.

## 주의

- reporting stack은 현재 삭제된 상태다.
- S3 `processed/` 입력과 `reports/daily/` 산출물은 destroy 대상이 아니며 보존된다.
- Dashboard page 및 Dashboard VPC 구현은 별도 담당 범위다.
