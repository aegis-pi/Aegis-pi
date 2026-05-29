from __future__ import annotations

from datetime import datetime, timezone
import re

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
    draft_markdown = _insert_section_metric_tables(draft_markdown, report_context)
    draft_markdown = _normalize_report_terms(draft_markdown)
    draft_markdown = _remove_simple_metric_repetition(draft_markdown)
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


def _insert_section_metric_tables(markdown: str, report_context: dict) -> str:
    section_tables = (
        ("## 데이터 수집 상태", _render_data_collection_table(report_context)),
        ("## Risk Score", _render_risk_score_table(report_context)),
        ("## 센서 및 AI 이벤트", _render_sensor_ai_table(report_context)),
        ("## 인프라 상태", _render_infra_table(report_context)),
        ("## 주요 이벤트", _render_events_table(report_context)),
        ("## 확인 필요 항목", _render_recommended_checks_table(report_context)),
    )
    for heading, table in section_tables:
        markdown = _insert_table_after_heading(markdown, heading, table)
    return markdown


def _insert_table_after_heading(markdown: str, heading: str, table: str) -> str:
    if not table or table in markdown:
        return markdown
    heading_text = re.escape(heading.strip())
    pattern = re.compile(rf"(?m)^({heading_text})[ \t]*\r?\n")
    match = pattern.search(markdown)
    if not match:
        return markdown
    insert_at = match.end()
    normalized_heading = match.group(1)
    return f"{markdown[:match.start()]}{normalized_heading}\n\n{table}\n\n{markdown[insert_at:]}"


def _normalize_report_terms(markdown: str) -> str:
    replacements = {
        "Risk degradation window sensor and AI causes": "Risk 저하 구간 원인 분석",
        "AI score spike source review": "AI 스코어 급등 원인 검토",
        "Abnormal sound sample review": "비정상 소리 샘플 검토",
        "Node readiness window evidence review": "노드 준비 상태 근거 검토",
        "edge-iot-publisher logs and K3s node status": "edge-iot-publisher 로그와 K3s 노드 상태 점검",
        "node_not_ready": "노드 준비 안됨",
        "unhealthy_workload": "비정상 워크로드",
        "workload_restart": "워크로드 재시작",
        "risk_degradation": "Risk 저하",
    }
    for source, target in replacements.items():
        markdown = markdown.replace(source, target)
    return markdown


def _remove_simple_metric_repetition(markdown: str) -> str:
    simple_metric_prefixes = {
        "## Risk Score": (
            "- 평균 Risk Score:",
            "- 최고 Risk Score:",
            "- 최저 Risk Score:",
            "- 주의 상태 누적 시간:",
            "- 위험 상태 누적 시간:",
            "- 평균 Risk Score는",
            "- 최저 Risk Score는",
            "- 최고 Risk Score는",
            "- 주의 상태(",
            "- 위험 상태(",
        ),
        "## 센서 및 AI 이벤트": (
            "- 온도 센서:",
            "- 습도 센서:",
            "- AI 스코어 급등 횟수:",
            "- 비정상 소리 감지 횟수:",
        ),
    }
    for heading, prefixes in simple_metric_prefixes.items():
        markdown = _replace_section_body(markdown, heading, lambda body, p=prefixes: _drop_lines_starting_with(body, p))
    return markdown


def _replace_section_body(markdown: str, heading: str, transform) -> str:
    marker = f"{heading}\n"
    start = markdown.find(marker)
    if start < 0:
        return markdown
    body_start = start + len(marker)
    next_heading = markdown.find("\n## ", body_start)
    if next_heading < 0:
        body = markdown[body_start:]
        return markdown[:body_start] + transform(body)
    body = markdown[body_start:next_heading]
    return markdown[:body_start] + transform(body).rstrip() + "\n" + markdown[next_heading:]


def _drop_lines_starting_with(body: str, prefixes: tuple[str, ...]) -> str:
    lines = []
    for line in body.splitlines():
        if line.strip().startswith(prefixes):
            continue
        lines.append(line)
    return "\n".join(lines).rstrip() + "\n"


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


def _render_data_collection_table(report_context: dict) -> str:
    data_quality = report_context.get("data_quality", {})
    rows = []
    for dataset, label in (
        ("factory_state", "공장 상태 데이터"),
        ("risk_score", "위험 점수 데이터"),
        ("infra_state", "인프라 상태 데이터"),
    ):
        actual = data_quality.get(f"{dataset}_actual_count")
        expected = data_quality.get(f"{dataset}_expected_count")
        rate = data_quality.get(f"{dataset}_collection_rate")
        if actual is not None and expected is not None and rate is not None:
            rows.append((label, f"{actual}/{expected}", _format_percent(rate), _collection_judgement(rate)))

    if data_quality.get("max_gap_minutes") is not None:
        rows.append(("최대 결측 구간", _gap_time_range(data_quality), f"{_format_number(data_quality.get('max_gap_minutes'))}분", _gap_judgement(data_quality.get("max_gap_minutes"))))

    if not rows:
        return ""
    return _render_markdown_table(("데이터", "수집량/구간", "수집률/시간", "판단"), rows, align=(None, "right", "right", None))


def _render_risk_score_table(report_context: dict) -> str:
    risk = report_context.get("risk", {})
    rows = []
    for label, key, judgement in (
        ("평균 Risk Score", "avg_score", "높을수록 안전에 가까움"),
        ("최저 Risk Score", "min_score", None),
        ("최고 Risk Score", "max_score", "정상 상한에 가까움"),
    ):
        if risk.get(key) is not None:
            rows.append((label, _format_number(risk.get(key)), judgement or _risk_judgement(risk.get(key))))
    if risk.get("warning_minutes") is not None:
        rows.append(("주의 상태 누적 시간", f"{_format_number(risk.get('warning_minutes'))}분", _minutes_judgement(risk.get("warning_minutes"), "원인 확인 필요", "주의 구간 없음")))
    if risk.get("danger_minutes") is not None:
        rows.append(("위험 상태 누적 시간", f"{_format_number(risk.get('danger_minutes'))}분", _minutes_judgement(risk.get("danger_minutes"), "즉시 확인 필요", "즉시 위험 아님")))
    if risk.get("min_score_time_ranges"):
        rows.append(("최저 점수 발생 시각", ", ".join(str(value) for value in risk.get("min_score_time_ranges", [])[:5]), "해당 시간대 우선 확인"))
    if risk.get("top_causes"):
        rows.append(("주요 원인 후보", ", ".join(str(value) for value in risk.get("top_causes", [])[:3]), "확정 원인 아님"))

    if not rows:
        return ""
    return _render_markdown_table(("항목", "값", "판단"), rows, align=(None, "right", None))


def _render_sensor_ai_table(report_context: dict) -> str:
    factory_state = report_context.get("factory_state", {})
    rows = []
    for label, key, suffix, judgement in (
        ("최고 온도", "temperature_max", "", "임계값과 현장 조건 확인"),
        ("최고 습도", "humidity_max", "%", "현장 조건 확인"),
        ("AI 스코어 급등", "ai_spike_event_count", "회", "원인 샘플 확인"),
        ("비정상 소리 감지", "abnormal_sound_count", "회", "소리 샘플 검토"),
        ("낙상 스코어 최고", "max_fall_score", "", "testbed/dummy 여부 구분"),
    ):
        value = factory_state.get(key)
        if value is not None:
            rows.append((label, f"{_format_number(value)}{suffix}", _count_judgement(value, judgement) if suffix == "회" else judgement))
    if factory_state.get("ai_spike_event_examples"):
        examples = factory_state.get("ai_spike_event_examples", [])[:3]
        ranges = [str(example.get("time_range")) for example in examples if example.get("time_range")]
        if ranges:
            rows.append(("AI 스코어 급등 예시", ", ".join(ranges), "예시 구간 우선 확인"))

    if not rows:
        return _render_markdown_table(("항목", "값", "판단"), [("센서/AI 이벤트", "없음", "context 기준 특이 이벤트 없음")], align=(None, "right", None))
    return _render_markdown_table(("항목", "값", "판단"), rows, align=(None, "right", None))


def _render_infra_table(report_context: dict) -> str:
    infra = report_context.get("infra", {})
    rows = []
    if infra.get("node_not_ready_count") is not None:
        value = f"{infra.get('node_not_ready_count')}회"
        if infra.get("node_not_ready_minutes") is not None:
            value += f", {_format_number(infra.get('node_not_ready_minutes'))}분"
        rows.append(("노드 준비 안됨", value, _count_judgement(infra.get("node_not_ready_count"), "원인 확인 필요")))
    if infra.get("workload_restart_total") is not None:
        rows.append(("워크로드 재시작", f"{infra.get('workload_restart_total')}회", _count_judgement(infra.get("workload_restart_total"), "재시작 원인 확인", "재시작 증거 없음")))
    if infra.get("unhealthy_workload_count") is not None:
        rows.append(("비정상 워크로드", f"{infra.get('unhealthy_workload_count')}개", _count_judgement(infra.get("unhealthy_workload_count"), "워크로드 상태 확인")))
    if infra.get("final_snapshot_status"):
        rows.append(("마지막 스냅샷 상태", str(infra.get("final_snapshot_status")), "현재 상태와 일중 이벤트를 분리해서 확인"))

    if not rows:
        return _render_markdown_table(("항목", "값", "판단"), [("인프라 이벤트", "없음", "context 기준 특이 이벤트 없음")], align=(None, "right", None))
    return _render_markdown_table(("항목", "값", "판단"), rows, align=(None, "right", None))


def _render_events_table(report_context: dict) -> str:
    events = report_context.get("events", [])[:5]
    if not events:
        return _render_markdown_table(("시간", "유형", "심각도", "지속", "근거"), [("-", "주요 이벤트 없음", "-", "-", "-")], align=(None, None, "right", "right", None))

    rows = []
    for event in events:
        rows.append((
            event.get("time_range") or "-",
            _event_type_label(event.get("type")),
            _format_number(event.get("severity_score")),
            _format_duration_seconds(event.get("duration_seconds")),
            _first_evidence_id(event),
        ))
    return _render_markdown_table(("시간", "유형", "심각도", "지속", "근거"), rows, align=(None, None, "right", "right", None))


def _render_recommended_checks_table(report_context: dict) -> str:
    checks = report_context.get("recommended_checks", [])[:5]
    if not checks:
        return _render_markdown_table(("우선순위", "항목", "이유", "근거"), [("-", "권장 확인 항목 없음", "-", "-")])

    rows = []
    for check in checks:
        rows.append((
            _priority_label(check.get("priority")),
            _check_item_label(check.get("item")),
            check.get("reason") or "-",
            _first_evidence_id(check),
        ))
    return _render_markdown_table(("우선순위", "항목", "이유", "근거"), rows)


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


def _gap_time_range(data_quality: dict) -> str:
    window = (data_quality.get("top_gap_windows") or [{}])[0]
    return window.get("time_range") or "-"


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


def _format_duration_seconds(value) -> str:
    if value is None:
        return "-"
    if value >= 60:
        return f"{_format_number(value / 60)}분"
    return f"{_format_number(value)}초"


def _event_type_label(value) -> str:
    labels = {
        "node_not_ready": "노드 준비 안됨",
        "unhealthy_workload": "비정상 워크로드",
        "workload_restart": "워크로드 재시작",
        "ai_spike": "AI 스코어 급등",
        "abnormal_sound": "비정상 소리 감지",
    }
    return labels.get(value, str(value or "-"))


def _priority_label(value) -> str:
    labels = {
        "high": "높음",
        "medium": "중간",
        "low": "낮음",
    }
    return labels.get(value, str(value or "-"))


def _check_item_label(value) -> str:
    labels = {
        "Risk degradation window sensor and AI causes": "Risk 저하 구간 원인 분석",
        "AI score spike source review": "AI 스코어 급등 원인 검토",
        "Abnormal sound sample review": "비정상 소리 샘플 검토",
        "Node readiness window evidence review": "노드 준비 상태 근거 검토",
        "edge-iot-publisher logs and K3s node status": "edge-iot-publisher 로그와 K3s 노드 상태 점검",
    }
    return labels.get(value, str(value or "-"))


def _first_evidence_id(item: dict) -> str:
    evidence_ids = item.get("evidence_message_ids")
    if evidence_ids:
        return str(evidence_ids[0])
    evidence = item.get("evidence") or {}
    evidence_ids = evidence.get("evidence_message_ids")
    if evidence_ids:
        return str(evidence_ids[0])
    return "-"


def _render_markdown_table(headers: tuple[str, ...], rows: list[tuple], align: tuple[str | None, ...] | None = None) -> str:
    align = align or tuple(None for _ in headers)
    separator = []
    for column_align in align:
        separator.append("---:" if column_align == "right" else "---")
    lines = [
        "| " + " | ".join(_escape_table_cell(header) for header in headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape_table_cell(value) for value in row) + " |")
    return "\n".join(lines)


def _escape_table_cell(value) -> str:
    if value is None:
        return "-"
    return str(value).replace("\n", " ").replace("|", "\\|")


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
