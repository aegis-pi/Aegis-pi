# Reporting Terraform Root

상태: implemented, pending validate/deploy
기준일: 2026-05-27

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
- `terraform validate` still needs to be rerun in an environment where provider plugins can execute.
- AWS deployment has not been run yet in the current session.
