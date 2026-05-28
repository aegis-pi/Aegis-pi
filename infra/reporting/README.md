# Reporting Terraform Root

상태: validated/deployed/manual-run-verified, currently destroyed
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

Current status:

- `terraform fmt -check -diff` passed.
- `terraform validate` passed in an environment where provider plugins can execute.
- AWS deployment was completed with `scripts/build/build-reporting.sh`.
- Manual Step Functions execution for `factory-b`, `report_date=2026-05-27`, `timezone=Asia/Seoul` succeeded.
- S3 outputs were verified under `reports/daily/yyyy=2026/mm=05/dd=27/factory-b/`.
- The reporting stack was later destroyed with `scripts/destroy/destroy-reporting.sh` to stop scheduled cost. S3 `processed/` input and `reports/daily/` output objects are preserved.

Cost baseline:

```text
docs/ops/25_daily_factory_report_cost.md
```
