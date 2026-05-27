# Daily Report Generator

상태: local implementation in progress
기준일: 2026-05-27

Bedrock based daily factory report generator.

MVP pipeline:

```text
PrepareReportWindow
  -> AggregateFactoryHour
  -> MergeFactoryDaily
  -> GenerateFactoryReport
```

The report pipeline reads S3 `processed/` data and writes factory daily
artifacts under `reports/daily/yyyy=YYYY/mm=MM/dd=DD/{factory_id}/`.
Bedrock receives only `report-context.json`.

Current local status:

- pytest passed: 9 tests.
- compileall passed for `apps/daily-report-generator`.
- `AggregateFactoryHour` emits structured infra summaries including not-ready nodes and unhealthy workloads.
- `MergeFactoryDaily` emits AI spike examples, likely infra causes, and rule-based recommended checks with evidence IDs where available.
- `PromptBuilder` instructs Bedrock to preserve evidence IDs, recommended checks, AI spike examples, S3 processed limitations, and testbed/dummy interpretation.

Pending:

- enriched v2 Bedrock live invocation.
- 24-hour daily merge validation.
- AWS deployment through `infra/reporting`.
