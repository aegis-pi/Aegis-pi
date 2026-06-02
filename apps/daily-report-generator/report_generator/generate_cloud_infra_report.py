from __future__ import annotations

from datetime import datetime, timezone

from report_generator.bedrock_client import BedrockReportClient
from report_generator.cloud_infra_prompt_builder import build_cloud_infra_prompt
from report_generator.cloud_infra_report_renderer import render_cloud_infra_markdown
from report_generator.cloud_infra_validation import validate_cloud_infra_report_invariants


def generate_cloud_infra_report(
    report_context: dict,
    output_prefix: str,
    bedrock_client: BedrockReportClient | None = None,
) -> dict:
    client = bedrock_client or BedrockReportClient()
    prompt = build_cloud_infra_prompt(report_context)
    generated_text = client.generate(prompt)
    narrative_errors = _validate_narrative_invariants(report_context, generated_text)
    markdown = render_cloud_infra_markdown(generated_text, report_context)
    validation_errors = validate_cloud_infra_report_invariants(report_context, markdown)
    validation_errors = [*narrative_errors, *validation_errors]
    if validation_errors:
        return {
            "target_id": report_context.get("target_id"),
            "report_date": report_context.get("report_date"),
            "status": "validation_failed",
            "validation_errors": validation_errors,
            "context_key": f"{output_prefix}/report-context.json",
        }

    report_key = f"{output_prefix}/report.md"
    metadata_key = f"{output_prefix}/generation-metadata.json"
    return {
        "target_id": report_context["target_id"],
        "report_date": report_context["report_date"],
        "status": "success",
        "report_key": report_key,
        "metadata_key": metadata_key,
        "markdown": markdown,
        "generation_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "model_id": getattr(client, "model_id", "mock"),
            "context_key": f"{output_prefix}/report-context.json",
            "report_key": report_key,
        },
    }


def _validate_narrative_invariants(report_context: dict, markdown: str) -> list[str]:
    errors = []
    for value in (report_context.get("report_date"),):
        if value and value not in markdown:
            errors.append(f"missing invariant value: {value}")
    return errors
