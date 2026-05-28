# Daily Report Generator

상태: validated
기준일: 2026-05-28

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

Current status:

- pytest passed: 10 tests.
- compileall passed for `apps/daily-report-generator`.
- Terraform `infra/reporting` fmt/init/validate passed.
- AWS reporting stack deployment and `factory-b` manual Step Functions execution passed.
- Reporting stack is currently destroyed to avoid scheduled cost; S3 `processed/` input and `reports/daily/` output are preserved.
- `AggregateFactoryHour` emits structured infra summaries including not-ready nodes and unhealthy workloads.
- `MergeFactoryDaily` emits AI spike examples, likely infra causes, and rule-based recommended checks with evidence IDs where available.
- `PromptBuilder` instructs Bedrock to preserve evidence IDs, recommended checks, AI spike examples, S3 processed limitations, and testbed/dummy interpretation.

Follow-up:

- Use `S3_GET_CONCURRENCY` for parallel S3 `GetObject`.
- Reduce `state_snapshot` reads to latest N or hour-end snapshots.
- Store Bedrock token usage and input object counts in `generation-metadata.json`.
