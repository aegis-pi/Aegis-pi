from __future__ import annotations

from datetime import datetime, timezone

from report_generator.bedrock_client import BedrockReportClient
from report_generator.prompt_builder import build_prompt
from report_generator.report_renderer import render_markdown_draft
from report_generator.validation import validate_report_invariants


def generate_factory_report(
    report_context: dict,
    output_prefix: str,
    bedrock_client: BedrockReportClient | None = None,
) -> dict:
    client = bedrock_client or BedrockReportClient()
    prompt = build_prompt(report_context)
    generated_text = client.generate(prompt)
    markdown = render_markdown_draft(generated_text)
    validation_errors = validate_report_invariants(report_context, markdown)
    if validation_errors:
        return {
            "factory_id": report_context.get("factory_id"),
            "report_date": report_context.get("report_date"),
            "status": "validation_failed",
            "validation_errors": validation_errors,
            "context_key": f"{output_prefix}/report-context.json",
        }

    report_key = f"{output_prefix}/report.md"
    metadata_key = f"{output_prefix}/generation-metadata.json"
    return {
        "factory_id": report_context["factory_id"],
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
