from __future__ import annotations

from collections import Counter
from datetime import datetime

from report_generator.severity import top_events


FACTORY_PROFILES = {
    "factory-a": {
        "environment_type": "physical-rpi",
        "input_module_type": "sensor",
        "interpretation_mode": "production_edge",
    },
    "factory-b": {
        "environment_type": "vm-mac",
        "input_module_type": "dummy",
        "interpretation_mode": "testbed_dummy",
    },
    "factory-c": {
        "environment_type": "vm-windows",
        "input_module_type": "dummy",
        "interpretation_mode": "testbed_dummy",
    },
}


def merge_factory_daily(
    factory_id: str,
    report_date: str,
    timezone: str,
    hourly_summaries: list[dict],
    output_prefix: str,
    max_context_events: int = 10,
) -> dict:
    ordered = sorted(hourly_summaries, key=lambda item: item.get("hour", ""))
    missing_hour_count = 24 - len({summary.get("hour") for summary in ordered})
    merged_events = merge_boundary_events(
        [event for summary in ordered for event in summary.get("events", [])]
    )
    scored_events = top_events(merged_events, max_context_events)

    daily_summary = {
        "schema_version": "0.1.0",
        "summary_type": "factory_daily",
        "factory_id": factory_id,
        "report_date": report_date,
        "timezone": timezone,
        "report_window": _report_window(ordered, timezone),
        "factory_profile": FACTORY_PROFILES.get(factory_id, _default_factory_profile()),
        "data_quality": _merge_data_quality(ordered, missing_hour_count),
        "risk": _merge_risk(ordered),
        "factory_state": _merge_factory_state(ordered),
        "infra": _merge_infra(ordered),
        "pipeline": _merge_pipeline(ordered),
        "snapshot": _merge_snapshot(ordered),
        "events": scored_events,
        "recommended_checks": _recommended_checks(scored_events, ordered),
        "data_limitations": _data_limitations(factory_id),
    }
    report_context = build_report_context(daily_summary, max_context_events)
    return {
        "factory_id": factory_id,
        "report_date": report_date,
        "status": "success",
        "daily_summary": daily_summary,
        "report_context": report_context,
        "daily_summary_key": f"{output_prefix}/factory-daily-summary.json",
        "context_key": f"{output_prefix}/report-context.json",
    }


def merge_boundary_events(events: list[dict], merge_gap_seconds: int = 120) -> list[dict]:
    grouped = {}
    passthrough = []
    for event in events:
        parsed = _parse_time_range(event.get("time_range", ""))
        if not parsed:
            passthrough.append(dict(event))
            continue
        key = (event.get("type"), event.get("severity"), event.get("summary"))
        grouped.setdefault(key, []).append((parsed[0], parsed[1], event))

    merged = passthrough
    for _, items in grouped.items():
        items.sort(key=lambda item: item[0])
        current_start, current_end, current_event = items[0]
        for start, end, event in items[1:]:
            gap = _minute_distance(current_end, start)
            if gap <= merge_gap_seconds / 60:
                current_end = max(current_end, end)
                current_event = _combine_events(current_event, event, current_start, current_end)
            else:
                merged.append(_with_time_range(current_event, current_start, current_end))
                current_start, current_end, current_event = start, end, event
        merged.append(_with_time_range(current_event, current_start, current_end))
    return merged


def build_report_context(daily_summary: dict, max_context_events: int) -> dict:
    context = {
        "schema_version": daily_summary["schema_version"],
        "context_type": "daily_factory_report",
        "factory_id": daily_summary["factory_id"],
        "report_date": daily_summary["report_date"],
        "timezone": daily_summary["timezone"],
        "report_window": daily_summary["report_window"],
        "factory_profile": daily_summary["factory_profile"],
        "data_quality": daily_summary["data_quality"],
        "risk": daily_summary["risk"],
        "factory_state": daily_summary["factory_state"],
        "infra": daily_summary["infra"],
        "pipeline": daily_summary["pipeline"],
        "snapshot": daily_summary["snapshot"],
        "events": daily_summary["events"][:max_context_events],
        "recommended_checks": daily_summary["recommended_checks"],
        "data_limitations": daily_summary["data_limitations"],
    }
    return context


def _report_window(summaries: list[dict], timezone: str) -> dict:
    if not summaries:
        return {
            "timezone": timezone,
            "start_local": None,
            "end_local": None,
            "start_utc": None,
            "end_utc": None,
            "s3_partition_timezone": "UTC",
        }
    first = summaries[0].get("hour_window", {})
    last = summaries[-1].get("hour_window", {})
    return {
        "timezone": timezone,
        "start_local": first.get("start_kst"),
        "end_local": last.get("end_kst"),
        "start_utc": first.get("start_utc") or first.get("start_kst"),
        "end_utc": last.get("end_utc") or last.get("end_kst"),
        "s3_partition_timezone": "UTC",
    }


def _merge_data_quality(summaries: list[dict], missing_hour_count: int) -> dict:
    expected = Counter()
    actual = Counter()
    invalid = 0
    duplicate = 0
    data_gap_count = 0
    max_gap_seconds = 0
    gap_windows = []
    gap_minutes_by_dataset = Counter()
    for summary in summaries:
        for dataset in ("factory_state", "risk_score", "infra_state"):
            expected[dataset] += summary.get("expected_counts", {}).get(dataset, 0) or 0
            actual[dataset] += summary.get("input_counts", {}).get(dataset, 0) or 0
        invalid += summary.get("input_counts", {}).get("invalid_records", 0) or 0
        duplicate += summary.get("input_counts", {}).get("duplicate_records", 0) or 0
        data_gap_count += summary.get("data_quality", {}).get("data_gap_count", 0) or 0
        max_gap_seconds = max(max_gap_seconds, summary.get("data_quality", {}).get("max_gap_seconds", 0) or 0)
        for window in summary.get("data_quality", {}).get("gap_windows", []):
            enriched = {**window, "hour": summary.get("hour")}
            gap_windows.append(enriched)
            gap_minutes_by_dataset[window.get("dataset", "unknown")] += float(window.get("duration_minutes", 0) or 0)

    gap_windows.sort(key=lambda item: item.get("duration_seconds", 0), reverse=True)

    return {
        "factory_state_expected_count": expected["factory_state"],
        "factory_state_actual_count": actual["factory_state"],
        "risk_score_expected_count": expected["risk_score"],
        "risk_score_actual_count": actual["risk_score"],
        "infra_state_expected_count": expected["infra_state"],
        "infra_state_actual_count": actual["infra_state"],
        "factory_state_collection_rate": _rate(actual["factory_state"], expected["factory_state"]),
        "risk_score_collection_rate": _rate(actual["risk_score"], expected["risk_score"]),
        "infra_state_collection_rate": _rate(actual["infra_state"], expected["infra_state"]),
        "missing_hour_count": missing_hour_count,
        "data_gap_count": data_gap_count,
        "max_gap_minutes": round(max_gap_seconds / 60, 2),
        "gap_minutes": round(sum(float(window.get("duration_seconds", 0) or 0) for window in gap_windows) / 60, 2),
        "gap_minutes_by_dataset": [
            {"dataset": dataset, "duration_minutes": round(minutes, 2)}
            for dataset, minutes in gap_minutes_by_dataset.most_common()
        ],
        "top_gap_windows": gap_windows[:10],
        "duplicate_message_count": duplicate,
        "invalid_record_count": invalid,
    }


def _merge_risk(summaries: list[dict]) -> dict:
    risks = [summary.get("risk", {}) for summary in summaries]
    avg_values = [(risk.get("avg_score"), summary.get("input_counts", {}).get("risk_score", 0) or 0) for summary, risk in zip(summaries, risks)]
    min_scores = [risk.get("min_score") for risk in risks if risk.get("min_score") is not None]
    max_scores = [risk.get("max_score") for risk in risks if risk.get("max_score") is not None]
    causes = Counter(cause for risk in risks for cause in risk.get("top_causes", []))
    warning_minutes = sum(risk.get("warning_minutes", 0) or 0 for risk in risks)
    danger_minutes = sum(risk.get("danger_minutes", 0) or 0 for risk in risks)
    worst_periods = [period for risk in risks for period in risk.get("worst_periods", [])]
    min_score = min(min_scores) if min_scores else None

    return {
        "avg_score": _weighted_average(avg_values),
        "min_score": min_score,
        "max_score": max(max_scores) if max_scores else None,
        "dominant_level": _dominant_level(warning_minutes, danger_minutes),
        "worst_level": _score_level(min_score),
        "warning_minutes": round(warning_minutes, 2),
        "danger_minutes": round(danger_minutes, 2),
        "top_causes": [cause for cause, _ in causes.most_common(5)],
        "worst_periods": sorted(worst_periods, key=lambda item: item.get("min_score", 100))[:5],
    }


def _merge_factory_state(summaries: list[dict]) -> dict:
    states = [summary.get("factory_state", {}) for summary in summaries]
    weighted = [
        (state.get("temperature_avg"), summary.get("input_counts", {}).get("factory_state", 0) or 0)
        for summary, state in zip(summaries, states)
    ]
    humidity_weighted = [
        (state.get("humidity_avg"), summary.get("input_counts", {}).get("factory_state", 0) or 0)
        for summary, state in zip(summaries, states)
    ]
    spike_events = [
        event
        for state in states
        for event in state.get("spike_events", [])
    ]
    spike_counts = Counter(event.get("summary", event.get("type", "unknown")) for event in spike_events)
    return {
        "temperature_avg": _weighted_average(weighted),
        "temperature_max": _max_value(states, "temperature_max"),
        "temperature_p95": _max_value(states, "temperature_p95"),
        "temperature_over_threshold_minutes": round(sum(state.get("temperature_over_threshold_minutes", 0) or 0 for state in states), 2),
        "humidity_avg": _weighted_average(humidity_weighted),
        "humidity_max": _max_value(states, "humidity_max"),
        "max_fire_score": _max_value(states, "max_fire_score"),
        "max_fall_score": _max_value(states, "max_fall_score"),
        "fall_score_p95": _max_value(states, "fall_score_p95"),
        "fall_score_over_threshold_seconds": sum(state.get("fall_score_over_threshold_seconds", 0) or 0 for state in states),
        "max_bend_score": _max_value(states, "max_bend_score"),
        "abnormal_sound_count": sum(state.get("abnormal_sound_count", 0) or 0 for state in states),
        "ai_spike_event_count": len(spike_events),
        "ai_spike_event_counts": [
            {"summary": summary, "count": count}
            for summary, count in spike_counts.most_common(10)
        ],
        "ai_spike_event_examples": _event_examples(spike_events, 5),
    }


def _merge_infra(summaries: list[dict]) -> dict:
    infra = [summary.get("infra", {}) for summary in summaries]
    not_ready_nodes = Counter()
    unhealthy_workloads = Counter()
    for item in infra:
        for node in item.get("not_ready_nodes", []):
            not_ready_nodes[node.get("node_id", "unknown")] += int(node.get("sample_count", 0) or 0)
        for workload in item.get("unhealthy_workloads", []):
            unhealthy_workloads[workload.get("workload", "unknown")] += int(workload.get("sample_count", 0) or 0)
    return {
        "node_not_ready_count": max((item.get("node_not_ready_count", 0) or 0 for item in infra), default=0),
        "node_not_ready_minutes": round(sum(item.get("node_not_ready_minutes", 0) or 0 for item in infra), 2),
        "workload_restart_total": sum(item.get("workload_restart_total", 0) or 0 for item in infra),
        "unhealthy_workload_minutes": round(sum(item.get("unhealthy_workload_minutes", 0) or 0 for item in infra), 2),
        "not_ready_nodes": [
            {"node_id": node_id, "sample_count": count}
            for node_id, count in not_ready_nodes.most_common(5)
        ],
        "unhealthy_workloads": [
            {"workload": workload, "sample_count": count}
            for workload, count in unhealthy_workloads.most_common(5)
        ],
        "likely_infra_causes": _likely_infra_causes(not_ready_nodes, unhealthy_workloads),
    }


def _merge_pipeline(summaries: list[dict]) -> dict:
    pipelines = [summary.get("pipeline", {}) for summary in summaries]
    return {
        "pipeline_warning_minutes": round(sum(item.get("pipeline_warning_minutes", 0) or 0 for item in pipelines), 2),
        "pipeline_critical_minutes": round(sum(item.get("pipeline_critical_minutes", 0) or 0 for item in pipelines), 2),
        "critical_gap_count": sum(1 for item in pipelines if (item.get("max_gap_seconds", 0) or 0) >= 300),
    }


def _merge_snapshot(summaries: list[dict]) -> dict:
    snapshots = [
        summary.get("snapshot", {})
        for summary in summaries
        if summary.get("snapshot", {}).get("state_snapshot_count", 0) > 0
    ]
    if not snapshots:
        return {
            "state_snapshot_count": 0,
            "final_updated_at": None,
            "last_factory_state_at": None,
            "last_infra_state_at": None,
            "final_risk_score": None,
            "final_risk_level": None,
            "final_pipeline_status": None,
            "final_nodes_ready": None,
            "final_nodes_total": None,
            "final_pods_ready": None,
            "final_pods_total": None,
        }
    final = max(snapshots, key=lambda item: item.get("final_updated_at") or "")
    return {
        **final,
        "state_snapshot_count": sum(item.get("state_snapshot_count", 0) or 0 for item in snapshots),
    }


def _recommended_checks(events: list[dict], summaries: list[dict]) -> list[dict]:
    checks = []
    event_types = {event.get("type") for event in events}
    evidence_by_type = _evidence_by_type(events)
    if "risk_degradation" in event_types:
        checks.append({
            "priority": "high",
            "item": "Risk degradation window sensor and AI causes",
            "reason": "Risk Score crossed warning threshold during the report window.",
            "evidence_message_ids": evidence_by_type.get("risk_degradation", [])[:2],
        })
    if "sensor_threshold_exceeded" in event_types:
        checks.append({
            "priority": "high",
            "item": "Temperature threshold exceedance cause",
            "reason": "Temperature exceeded configured warning threshold.",
            "evidence_message_ids": evidence_by_type.get("sensor_threshold_exceeded", [])[:2],
        })
    if "ai_score_spike" in event_types:
        checks.append({
            "priority": "medium",
            "item": "AI score spike source review",
            "reason": "One or more AI scores crossed the spike threshold.",
            "evidence_message_ids": evidence_by_type.get("ai_score_spike", [])[:2],
        })
    elif any((summary.get("factory_state", {}).get("ai_spike_event_count", 0) or len(summary.get("factory_state", {}).get("spike_events", []))) > 0 for summary in summaries):
        evidence = []
        for summary in summaries:
            for event in summary.get("factory_state", {}).get("spike_events", []):
                for message_id in event.get("evidence", {}).get("evidence_message_ids", []):
                    if message_id not in evidence:
                        evidence.append(message_id)
        checks.append({
            "priority": "medium",
            "item": "AI score spike source review",
            "reason": "AI spike events were present in factory_state summary even if they were not in top severity events.",
            "evidence_message_ids": evidence[:2],
        })
    if any(summary.get("factory_state", {}).get("abnormal_sound_count", 0) > 0 for summary in summaries):
        checks.append({
            "priority": "medium",
            "item": "Abnormal sound sample review",
            "reason": "abnormal_sound_count was greater than zero in factory_state.",
            "evidence_message_ids": [],
        })
    if "node_not_ready" in event_types:
        nodes = Counter()
        for summary in summaries:
            for node in summary.get("infra", {}).get("not_ready_nodes", []):
                nodes[node.get("node_id", "unknown")] += int(node.get("sample_count", 0) or 0)
        checks.append({
            "priority": "high",
            "item": "Node readiness window evidence review",
            "reason": "node_not_ready events were detected in infra_state.",
            "target_nodes": [node for node, _ in nodes.most_common(3)],
            "evidence_message_ids": evidence_by_type.get("node_not_ready", [])[:2],
        })
    if "workload_unhealthy" in event_types:
        checks.append({
            "priority": "medium",
            "item": "Unhealthy workload status review",
            "reason": "workload_unhealthy events were detected in infra_state.",
            "evidence_message_ids": evidence_by_type.get("workload_unhealthy", [])[:2],
        })
    if any(summary.get("pipeline", {}).get("max_gap_seconds", 0) >= 300 for summary in summaries):
        checks.append({
            "priority": "medium",
            "item": "edge-iot-publisher logs and K3s node status",
            "reason": "A data gap of at least five minutes was detected.",
            "evidence_message_ids": evidence_by_type.get("data_gap", [])[:2],
        })
    if any(summary.get("infra", {}).get("workload_restart_total", 0) >= 3 for summary in summaries):
        checks.append({
            "priority": "medium",
            "item": "Restarted workload logs",
            "reason": "Workload restart delta exceeded review threshold.",
            "evidence_message_ids": evidence_by_type.get("workload_unhealthy", [])[:2],
        })
    return checks[:5]


def _likely_infra_causes(not_ready_nodes: Counter, unhealthy_workloads: Counter) -> list[dict]:
    causes = []
    for node_id, count in not_ready_nodes.most_common(3):
        causes.append({
            "type": "node_not_ready",
            "target": node_id,
            "sample_count": count,
            "interpretation": "Node ready=false was observed in infra_state samples.",
        })
    for workload, count in unhealthy_workloads.most_common(3):
        causes.append({
            "type": "workload_unhealthy",
            "target": workload,
            "sample_count": count,
            "interpretation": "Workload ready/status indicated unhealthy state in infra_state samples.",
        })
    return causes


def _evidence_by_type(events: list[dict]) -> dict[str, list[str]]:
    result = {}
    for event in events:
        event_type = event.get("type", "unknown")
        result.setdefault(event_type, [])
        for message_id in event.get("evidence", {}).get("evidence_message_ids", []):
            if message_id not in result[event_type]:
                result[event_type].append(message_id)
    return result


def _event_examples(events: list[dict], limit: int) -> list[dict]:
    examples = []
    for event in events[:limit]:
        examples.append({
            "type": event.get("type"),
            "summary": event.get("summary"),
            "time_range": event.get("time_range"),
            "duration_seconds": event.get("duration_seconds"),
            "evidence_message_ids": event.get("evidence", {}).get("evidence_message_ids", [])[:2],
        })
    return examples


def _data_limitations(factory_id: str) -> list[str]:
    limitations = [
        "Report is based on S3 processed data, not S3 raw payloads.",
        "LLM output is an operational draft and requires operator review.",
    ]
    if factory_id in ("factory-b", "factory-c"):
        limitations.append("factory-b/c use testbed dummy data and must be interpreted separately from physical sensor data.")
    return limitations


def _combine_events(left: dict, right: dict, start: int, end: int) -> dict:
    evidence_ids = []
    for event in (left, right):
        evidence_ids.extend(event.get("evidence", {}).get("evidence_message_ids", []))
    combined = dict(left)
    combined["duration_seconds"] = (end - start + 1) * 60
    combined["magnitude"] = max(float(left.get("magnitude", 0) or 0), float(right.get("magnitude", 0) or 0))
    combined["evidence"] = {"evidence_message_ids": evidence_ids[:10]}
    return combined


def _with_time_range(event: dict, start: int, end: int) -> dict:
    updated = dict(event)
    updated["time_range"] = f"{start // 60:02d}:{start % 60:02d}~{end // 60:02d}:{end % 60:02d}"
    updated["duration_seconds"] = max(updated.get("duration_seconds", 0) or 0, (end - start + 1) * 60)
    return updated


def _parse_time_range(value: str) -> tuple[int, int] | None:
    if "~" not in value:
        return None
    start, end = value.split("~", 1)
    try:
        return _parse_hhmm(start), _parse_hhmm(end)
    except ValueError:
        return None


def _parse_hhmm(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _minute_distance(left_end: int, right_start: int) -> int:
    return right_start - left_end - 1


def _rate(actual: int, expected: int) -> float:
    return round(actual / expected, 4) if expected else 0.0


def _weighted_average(values: list[tuple[float | None, int]]) -> float | None:
    numerator = 0.0
    denominator = 0
    for value, weight in values:
        if value is None or weight <= 0:
            continue
        numerator += float(value) * weight
        denominator += weight
    return round(numerator / denominator, 2) if denominator else None


def _max_value(items: list[dict], key: str):
    values = [item.get(key) for item in items if item.get(key) is not None]
    return max(values) if values else None


def _dominant_level(warning_minutes: float, danger_minutes: float) -> str:
    if danger_minutes > 0:
        return "danger"
    if warning_minutes > 0:
        return "warning"
    return "normal"


def _score_level(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score < 50:
        return "danger"
    if score < 85:
        return "warning"
    return "normal"


def _default_factory_profile() -> dict:
    return {
        "environment_type": "unknown",
        "input_module_type": "unknown",
        "interpretation_mode": "unknown",
    }
