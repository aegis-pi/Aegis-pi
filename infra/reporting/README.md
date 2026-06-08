# Reporting Terraform Root

상태: validated/deployed/manual-run-verified, Terraform plan clean
기준일: 2026-05-28

Bedrock based daily factory report pipeline.

This root module intentionally does not read foundation remote state. It looks up
the existing data bucket through `var.data_bucket_name` and `data.aws_s3_bucket`.

Default region: `ap-south-1`

Pipeline:

```text
EventBridge Scheduler
  -> Step Functions DailyFactoryReportStateMachine
      -> PrepareReportWindow
      -> AggregateFactoryHour
      -> MergeFactoryDaily
      -> GenerateFactoryReport
```

Outputs are stored under:

```text
reports/daily/yyyy=YYYY/mm=MM/dd=DD/{factory_id}/
```

Infrastructure status in the current report is derived from S3 processed
`infra_state` and `state_snapshot` data. A planned extension is to add
CloudWatch Logs/metrics as a secondary source for reporting pipeline health:
Lambda/Step Functions errors, timeouts, retries, and duration should be
summarized in `report-context.json` without embedding raw log lines. The report
should keep factory infrastructure interpretation from processed data separate
from AWS reporting pipeline health observed through CloudWatch.

Current status:

- `terraform fmt -check -diff` passed.
- `terraform validate` passed in an environment where provider plugins can execute.
- `python -m compileall -q apps/daily-report-generator` passed.
- `python -m pytest -q apps/daily-report-generator` passed with 11 tests.
- AWS deployment was completed with `scripts/build/build-reporting.sh`.
- Manual Step Functions execution `manual-factory-report-20260528T064840Z` for `factory-b`, `report_date=2026-05-27`, `timezone=Asia/Seoul` succeeded.
- S3 outputs were verified under `reports/daily/yyyy=2026/mm=05/dd=27/factory-b/`.
- The generated `report.md` was verified to include the key metrics, data collection, Risk Score, sensor/AI, infrastructure, events, and recommended-check tables plus narrative analysis.
- Current Terraform refresh-only and normal plans are clean against the deployed AWS resources. S3 `processed/` input and `reports/daily/` output objects are preserved.

Cost baseline:

```text
docs/ops/25_daily_factory_report_cost.md
```
