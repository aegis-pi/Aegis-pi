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
    draft_markdown = _insert_key_metrics_table(draft_markdown, report_context)
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


def _insert_key_metrics_table(markdown: str, report_context: dict) -> str:
    if "## 핵심 지표 표" in markdown:
        return markdown

    table = _render_key_metrics_table(report_context)
    marker = "\n## 데이터 수집 상태"
    if marker in markdown:
        head, tail = markdown.split(marker, 1)
        return f"{head.rstrip()}\n\n{table}\n{marker}{tail}"
    return markdown.rstrip() + "\n\n" + table + "\n"


def _render_key_metrics_table(report_context: dict) -> str:
    data_quality = report_context.get("data_quality", {})
    risk = report_context.get("risk", {})
    factory_state = report_context.get("factory_state", {})
    infra = report_context.get("infra", {})
    pipeline = report_context.get("pipeline", {})

    rows = [
        ("전체 상태", _overall_status(data_quality, risk, infra, pipeline), _overall_judgement(data_quality, risk, infra, pipeline)),
    ]

    if risk.get("avg_score") is not None:
        rows.append(("평균 Risk Score", _format_number(risk.get("avg_score")), "높을수록 안전에 가까움"))
    if risk.get("min_score") is not None:
        rows.append(("최저 Risk Score", _format_number(risk.get("min_score")), _risk_judgement(risk.get("min_score"))))
    if risk.get("warning_minutes") is not None:
        rows.append(("주의 상태 누적 시간", f"{_format_number(risk.get('warning_minutes'))}분", _minutes_judgement(risk.get("warning_minutes"), "원인 확인 필요", "주의 구간 없음")))
    if risk.get("danger_minutes") is not None:
        rows.append(("위험 상태 누적 시간", f"{_format_number(risk.get('danger_minutes'))}분", _minutes_judgement(risk.get("danger_minutes"), "즉시 확인 필요", "즉시 위험 아님")))

    for dataset, label in (
        ("factory_state", "공장 상태 데이터 수집률"),
        ("risk_score", "위험 점수 데이터 수집률"),
        ("infra_state", "인프라 상태 데이터 수집률"),
    ):
        value = _collection_value(data_quality, dataset)
        if value:
            rows.append((label, value, _collection_judgement(data_quality.get(f"{dataset}_collection_rate"))))

    if data_quality.get("max_gap_minutes") is not None:
        rows.append(("최대 결측 구간", _gap_value(data_quality), _gap_judgement(data_quality.get("max_gap_minutes"))))
    if factory_state.get("ai_spike_event_count") is not None:
        rows.append(("AI 스코어 급등", f"{factory_state.get('ai_spike_event_count')}회", _count_judgement(factory_state.get("ai_spike_event_count"), "확인 필요")))
    if factory_state.get("abnormal_sound_count") is not None:
        rows.append(("비정상 소리 감지", f"{factory_state.get('abnormal_sound_count')}회", _count_judgement(factory_state.get("abnormal_sound_count"), "샘플 검토 필요")))
    if infra.get("node_not_ready_count") is not None:
        value = f"{infra.get('node_not_ready_count')}회"
        if infra.get("node_not_ready_minutes") is not None:
            value += f", {_format_number(infra.get('node_not_ready_minutes'))}분"
        rows.append(("노드 준비 안됨", value, _count_judgement(infra.get("node_not_ready_count"), "원인 확인 필요")))
    if infra.get("workload_restart_total") is not None:
        rows.append(("워크로드 재시작", f"{infra.get('workload_restart_total')}회", _count_judgement(infra.get("workload_restart_total"), "재시작 원인 확인", "재시작 증거 없음")))

    lines = [
        "## 핵심 지표 표",
        "",
        "| 구분 | 값 | 판단 |",
        "| --- | ---: | --- |",
    ]
    lines.extend(f"| {label} | {value} | {judgement} |" for label, value, judgement in rows)
    return "\n".join(lines)


def _overall_status(data_quality: dict, risk: dict, infra: dict, pipeline: dict) -> str:
    if _positive(risk.get("danger_minutes")):
        return "위험"
    if (
        _positive(risk.get("warning_minutes"))
        or _positive(data_quality.get("data_gap_count"))
        or _positive(pipeline.get("pipeline_critical_minutes"))
        or _positive(infra.get("node_not_ready_count"))
        or _positive(infra.get("workload_restart_total"))
    ):
        return "주의"
    return "정상"


def _overall_judgement(data_quality: dict, risk: dict, infra: dict, pipeline: dict) -> str:
    status = _overall_status(data_quality, risk, infra, pipeline)
    if status == "위험":
        return "위험 구간 즉시 확인 필요"
    if status == "주의":
        return "위험은 아니지만 결측/주의 구간/인프라 이벤트 확인 필요"
    return "특이 이벤트 없음"


def _collection_value(data_quality: dict, dataset: str) -> str | None:
    actual = data_quality.get(f"{dataset}_actual_count")
    expected = data_quality.get(f"{dataset}_expected_count")
    rate = data_quality.get(f"{dataset}_collection_rate")
    if actual is None or expected is None or rate is None:
        return None
    return f"{actual}/{expected}, {_format_percent(rate)}"


def _collection_judgement(rate) -> str:
    if rate is None:
        return "확인 필요"
    if rate >= 0.99:
        return "양호"
    if rate >= 0.95:
        return "일부 결측"
    return "결측 영향 확인 필요"


def _gap_value(data_quality: dict) -> str:
    window = (data_quality.get("top_gap_windows") or [{}])[0]
    if window.get("time_range"):
        return f"{window.get('time_range')}, {_format_number(data_quality.get('max_gap_minutes'))}분"
    return f"{_format_number(data_quality.get('max_gap_minutes'))}분"


def _gap_judgement(minutes) -> str:
    if _positive(minutes):
        return "데이터 공백 확인 필요"
    return "긴 결측 없음"


def _risk_judgement(score) -> str:
    if score is None:
        return "확인 필요"
    if score < 60:
        return "위험 기준 접근"
    if score < 80:
        return "주의 기준 진입"
    return "양호"


def _minutes_judgement(minutes, positive_text: str, zero_text: str) -> str:
    return positive_text if _positive(minutes) else zero_text


def _count_judgement(count, positive_text: str, zero_text: str = "발생 없음") -> str:
    return positive_text if _positive(count) else zero_text


def _positive(value) -> bool:
    return value is not None and value > 0


def _format_percent(value) -> str:
    return f"{value * 100:.2f}%"


def _format_number(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


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
