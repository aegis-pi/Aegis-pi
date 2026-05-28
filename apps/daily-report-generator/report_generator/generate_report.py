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
    draft_markdown = render_markdown_draft(generated_text)
    narrative_errors = _validate_narrative_invariants(report_context, draft_markdown)
    markdown = _append_verification_metrics(draft_markdown, report_context)
    validation_errors = validate_report_invariants(report_context, markdown)
    validation_errors = [*narrative_errors, *validation_errors]
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


def _validate_narrative_invariants(report_context: dict, markdown: str) -> list[str]:
    errors = []
    for value in (report_context.get("factory_id"), report_context.get("report_date")):
        if value and value not in markdown:
            errors.append(f"missing invariant value: {value}")
    return errors


def _append_verification_metrics(markdown: str, report_context: dict) -> str:
    risk = report_context.get("risk", {})
    data_quality = report_context.get("data_quality", {})
    report_window = report_context.get("report_window", {})
    lines = [
        "",
        "## 검증 기준 수치",
        "",
        "- 이 섹션은 보고서 검증을 위해 context 원문 수치를 그대로 남긴다. 위 본문 해석과 함께 확인한다.",
    ]
    if report_window:
        lines.append(
            "- 보고서 window 원문: "
            f"timezone={report_window.get('timezone')}, "
            f"start_local={report_window.get('start_local')}, "
            f"end_local={report_window.get('end_local')}, "
            f"start_utc={report_window.get('start_utc')}, "
            f"end_utc={report_window.get('end_utc')}"
        )
    if risk:
        risk_parts = []
        for label, key in (
            ("avg_score", "avg_score"),
            ("min_score", "min_score"),
            ("max_score", "max_score"),
            ("warning_minutes", "warning_minutes"),
            ("danger_minutes", "danger_minutes"),
        ):
            if risk.get(key) is not None:
                risk_parts.append(f"{label}={risk[key]}")
        if risk_parts:
            lines.append(f"- Risk Score 원문: {', '.join(risk_parts)}")

    for dataset in ("factory_state", "risk_score", "infra_state"):
        actual = data_quality.get(f"{dataset}_actual_count")
        expected = data_quality.get(f"{dataset}_expected_count")
        rate = data_quality.get(f"{dataset}_collection_rate")
        if actual is not None and expected is not None and rate is not None:
            lines.append(f"- {dataset} 수집 원문: {actual}/{expected}, collection_rate {rate}")

    if data_quality.get("missing_hour_count") is not None:
        lines.append(f"- missing_hour_count 원문: {data_quality['missing_hour_count']}")
    if data_quality.get("max_gap_minutes") is not None:
        lines.append(f"- max_gap_minutes 원문: {data_quality['max_gap_minutes']}")
    for index, window in enumerate(data_quality.get("top_gap_windows", [])[:5], start=1):
        lines.append(
            "- top_gap_window 원문 "
            f"{index}: dataset={window.get('dataset')}, time_range={window.get('time_range')}, "
            f"duration_minutes={window.get('duration_minutes')}, gap_type={window.get('gap_type')}"
        )

    return markdown.rstrip() + "\n" + "\n".join(lines) + "\n"
