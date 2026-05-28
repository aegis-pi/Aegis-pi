from __future__ import annotations

from collections import Counter

from report_generator.config import AggregateThresholds, aggregate_thresholds_from_env
from report_generator.event_detection import threshold_windows
from report_generator.reducers import NumericReducer, max_gap_seconds
from report_generator.severity import top_events
from report_generator.time_window import parse_timestamp, parse_window_bound

DATASETS = ("factory_state", "risk_score", "infra_state")
AUX_DATASETS = ("state_snapshot",)


def aggregate_factory_hour_records(
    factory_id: str,
    report_date: str,
    timezone: str,
    hour: str,
    hour_window: dict,
    records_by_dataset: dict[str, list[dict]],
    output_prefix: str | None = None,
    thresholds: AggregateThresholds | None = None,
) -> dict:
    thresholds = thresholds or aggregate_thresholds_from_env()
    start = parse_window_bound(hour_window["start_kst"])
    end = parse_window_bound(hour_window["end_kst"])
    end_exclusive = _exclusive_end(end)

    normalized = {}
    invalid_records = 0
    duplicate_records = 0
    for dataset in (*DATASETS, *AUX_DATASETS):
        dataset_records, invalid, duplicate = _valid_unique_records(
            records_by_dataset.get(dataset, []), factory_id, start, end_exclusive
        )
        normalized[dataset] = dataset_records
        invalid_records += invalid
        duplicate_records += duplicate

    expected_counts = {
        "factory_state": 3600 // thresholds.factory_state_interval_seconds,
        "risk_score": 3600 // thresholds.risk_score_interval_seconds,
        "infra_state": 3600 // thresholds.infra_state_interval_seconds,
    }
    input_counts = {dataset: len(normalized[dataset]) for dataset in DATASETS}
    input_counts["state_snapshot"] = len(normalized["state_snapshot"])
    input_counts["invalid_records"] = invalid_records
    input_counts["duplicate_records"] = duplicate_records

    summary = {
        "schema_version": "0.1.0",
        "summary_type": "factory_hour",
        "factory_id": factory_id,
        "report_date": report_date,
        "timezone": timezone,
        "hour": hour,
        "hour_window": hour_window,
        "status": "empty" if sum(len(normalized[dataset]) for dataset in DATASETS) == 0 else "success",
        "input_counts": input_counts,
        "expected_counts": expected_counts,
        "data_quality": _data_quality(normalized, expected_counts, start, end_exclusive, thresholds, timezone),
        "risk": _risk_summary(normalized["risk_score"], thresholds, timezone),
        "factory_state": _factory_state_summary(normalized["factory_state"], thresholds, timezone),
        "infra": _infra_summary(normalized["infra_state"], thresholds),
        "snapshot": _snapshot_summary(normalized["state_snapshot"]),
    }
    summary["pipeline"] = _pipeline_summary(normalized, thresholds, summary["data_quality"])
    summary["events"] = _events(summary, normalized, thresholds, timezone)
    if output_prefix:
        summary["summary_key"] = f"{output_prefix}/intermediate/hourly/hh={hour}.json"
    return summary


def _valid_unique_records(records: list[dict], factory_id: str, start, end_exclusive) -> tuple[list[dict], int, int]:
    valid = []
    seen = set()
    invalid = 0
    duplicate = 0
    for record in records:
        try:
            if record.get("factory_id") != factory_id:
                continue
            timestamp = parse_timestamp(record.get("source_timestamp") or record.get("processed_at") or record.get("updated_at"))
            if timestamp < start or timestamp >= end_exclusive:
                continue
            message_id = record.get("source_message_id") or record.get("message_id") or record.get("sk") or record.get("updated_at")
            if not message_id:
                raise ValueError("missing message id")
        except Exception:
            invalid += 1
            continue
        if message_id in seen:
            duplicate += 1
            continue
        seen.add(message_id)
        valid.append({**record, "_timestamp": timestamp, "_message_id": message_id})
    valid.sort(key=lambda item: item["_timestamp"])
    return valid, invalid, duplicate


def _exclusive_end(end):
    from datetime import timedelta

    return end + timedelta(seconds=1)


def _data_quality(
    records_by_dataset: dict[str, list[dict]],
    expected_counts: dict[str, int],
    start,
    end,
    thresholds: AggregateThresholds,
    timezone_name: str,
) -> dict:
    quality = {}
    all_gaps = []
    gap_windows = []
    for dataset in DATASETS:
        actual = len(records_by_dataset[dataset])
        expected = expected_counts[dataset]
        quality[f"{dataset}_collection_rate"] = round(actual / expected, 4) if expected else 0
        expected_gap = (
            thresholds.infra_state_interval_seconds
            if dataset == "infra_state"
            else thresholds.factory_state_interval_seconds
        )
        dataset_gap_windows = _gap_windows_for_dataset(
            dataset=dataset,
            records=records_by_dataset[dataset],
            start=start,
            end=end,
            expected_gap_seconds=expected_gap,
            timezone_name=timezone_name,
        )
        gap_windows.extend(dataset_gap_windows)
        all_gaps.extend(int(window["duration_seconds"]) for window in dataset_gap_windows)
        legacy_gap = max_gap_seconds(record["_timestamp"] for record in records_by_dataset[dataset])
        if legacy_gap:
            all_gaps.append(legacy_gap)
        quality[f"{dataset}_gap_minutes"] = round(
            sum(float(window["duration_seconds"]) for window in dataset_gap_windows) / 60,
            2,
        )

    gap_windows.sort(key=lambda window: window["duration_seconds"], reverse=True)
    quality["data_gap_count"] = len(gap_windows)
    quality["max_gap_seconds"] = max(all_gaps) if all_gaps else 0
    quality["max_gap_minutes"] = round(quality["max_gap_seconds"] / 60, 2)
    quality["gap_minutes"] = round(sum(float(window["duration_seconds"]) for window in gap_windows) / 60, 2)
    quality["gap_windows"] = gap_windows[:10]
    return quality


def _gap_windows_for_dataset(
    *,
    dataset: str,
    records: list[dict],
    start,
    end,
    expected_gap_seconds: int,
    timezone_name: str,
) -> list[dict]:
    if not records:
        return [
            _gap_window(
                dataset=dataset,
                start=start,
                end=end,
                gap_type="hour_empty",
                timezone_name=timezone_name,
            )
        ]

    windows = []
    first = records[0]["_timestamp"]
    if (first - start).total_seconds() > expected_gap_seconds * 2:
        windows.append(_gap_window(dataset, start, first, "hour_start", timezone_name))

    for left, right in zip(records, records[1:]):
        gap_seconds = int((right["_timestamp"] - left["_timestamp"]).total_seconds())
        if gap_seconds > expected_gap_seconds * 2:
            windows.append(_gap_window(dataset, left["_timestamp"], right["_timestamp"], "internal", timezone_name))

    last = records[-1]["_timestamp"]
    if (end - last).total_seconds() > expected_gap_seconds * 2:
        windows.append(_gap_window(dataset, last, end, "hour_end", timezone_name))

    return windows


def _gap_window(dataset: str, start, end, gap_type: str, timezone_name: str) -> dict:
    from report_generator.time_window import format_hhmm_range

    duration_seconds = max(int((end - start).total_seconds()), 0)
    return {
        "dataset": dataset,
        "gap_type": gap_type,
        "start_utc": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end_utc": end.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "time_range": format_hhmm_range(start, end, timezone_name),
        "duration_seconds": duration_seconds,
        "duration_minutes": round(duration_seconds / 60, 2),
    }


def _risk_summary(records: list[dict], thresholds: AggregateThresholds, timezone_name: str) -> dict:
    scores = NumericReducer()
    causes = Counter()
    samples = []
    for record in records:
        risk = record.get("risk", {})
        score = risk.get("score")
        scores.add(score)
        for cause in risk.get("top_causes", []):
            causes[str(cause.get("field", "unknown"))] += 1
        samples.append({
            "timestamp": record["_timestamp"],
            "message_id": record["_message_id"],
            "score": score,
        })
    result = _rename_score_stats(scores.summary("score"))
    result["warning_minutes"] = round(_duration_seconds(records, thresholds.risk_score_interval_seconds, lambda r: _risk_level(r, thresholds) == "warning") / 60, 2)
    result["danger_minutes"] = round(_duration_seconds(records, thresholds.risk_score_interval_seconds, lambda r: _risk_level(r, thresholds) == "danger") / 60, 2)
    result["top_causes"] = [cause for cause, _ in causes.most_common(5)]
    result["worst_periods"] = []
    if records:
        worst = min(records, key=lambda item: float(item.get("risk", {}).get("score", 100)))
        result["worst_periods"].append({
            "time_range": _single_time_range(worst["_timestamp"], timezone_name),
            "min_score": worst.get("risk", {}).get("score"),
            "level": _risk_level(worst, thresholds),
            "top_causes": [cause.get("field") for cause in worst.get("risk", {}).get("top_causes", [])],
            "evidence_message_ids": [worst["_message_id"]],
        })
    return result


def _factory_state_summary(records: list[dict], thresholds: AggregateThresholds, timezone_name: str) -> dict:
    reducers = {
        "temperature": NumericReducer(),
        "humidity": NumericReducer(),
        "pressure": NumericReducer(),
        "fire_score": NumericReducer(),
        "fall_score": NumericReducer(),
        "bend_score": NumericReducer(),
    }
    samples = []
    abnormal_sound_count = 0
    for record in records:
        data = record.get("data", {})
        reducers["temperature"].add(data.get("temperature_celsius"))
        reducers["humidity"].add(data.get("humidity_percent"))
        reducers["pressure"].add(data.get("pressure_hpa"))
        reducers["fire_score"].add(data.get("fire_score"))
        reducers["fall_score"].add(data.get("fall_score"))
        reducers["bend_score"].add(data.get("bend_score"))
        if data.get("abnormal_sound") not in (None, "", "none"):
            abnormal_sound_count += 1
        samples.append({
            "timestamp": record["_timestamp"],
            "message_id": record["_message_id"],
            **data,
        })

    temperature = reducers["temperature"].summary("temperature")
    humidity = reducers["humidity"].summary("humidity")
    pressure = reducers["pressure"].summary("pressure")
    fire = reducers["fire_score"].summary("fire_score")
    fall = reducers["fall_score"].summary("fall_score")
    bend = reducers["bend_score"].summary("bend_score")

    spike_events = []
    for score_field in ("fire_score", "fall_score", "bend_score"):
        spike_events.extend(threshold_windows(
            samples,
            lambda sample, field=score_field: float(sample.get(field) or 0) >= thresholds.ai_score_spike_threshold,
            thresholds.factory_state_interval_seconds,
            timezone_name,
            "ai_score_spike",
            "warning",
            f"{score_field} exceeded spike threshold",
            lambda items, field=score_field: round(max(float(item.get(field) or 0) for item in items) * 10, 2),
        ))

    return {
        "temperature_avg": temperature["temperature_avg"],
        "temperature_min": temperature["temperature_min"],
        "temperature_max": temperature["temperature_max"],
        "temperature_p05": temperature["temperature_p05"],
        "temperature_p95": temperature["temperature_p95"],
        "temperature_over_threshold_minutes": round(_sample_duration_seconds(samples, thresholds.factory_state_interval_seconds, lambda item: float(item.get("temperature_celsius") or 0) >= thresholds.temperature_warning_c) / 60, 2),
        "humidity_avg": humidity["humidity_avg"],
        "humidity_min": humidity["humidity_min"],
        "humidity_max": humidity["humidity_max"],
        "humidity_p05": humidity["humidity_p05"],
        "humidity_p95": humidity["humidity_p95"],
        "pressure_min": pressure["pressure_min"],
        "pressure_max": pressure["pressure_max"],
        "max_fire_score": fire["fire_score_max"],
        "fire_score_p95": fire["fire_score_p95"],
        "max_fall_score": fall["fall_score_max"],
        "fall_score_p95": fall["fall_score_p95"],
        "fall_score_over_threshold_seconds": _sample_duration_seconds(samples, thresholds.factory_state_interval_seconds, lambda item: float(item.get("fall_score") or 0) >= thresholds.ai_score_spike_threshold),
        "max_bend_score": bend["bend_score_max"],
        "bend_score_p95": bend["bend_score_p95"],
        "abnormal_sound_count": abnormal_sound_count,
        "spike_events": spike_events,
    }


def _infra_summary(records: list[dict], thresholds: AggregateThresholds) -> dict:
    node_not_ready_count = 0
    unhealthy_sample_count = 0
    restart_values = []
    not_ready_nodes = Counter()
    unhealthy_workloads = Counter()
    for record in records:
        data = record.get("data", {})
        nodes_total = int(data.get("nodes_total", 0) or 0)
        nodes_ready = int(data.get("nodes_ready", 0) or 0)
        node_not_ready_count = max(node_not_ready_count, max(nodes_total - nodes_ready, 0))
        for node in data.get("nodes", []):
            if not bool(node.get("ready", False)):
                not_ready_nodes[_node_label(node)] += 1
        pods_total = int(data.get("pods_total", 0) or 0)
        pods_ready = int(data.get("pods_ready", 0) or 0)
        if pods_total and pods_ready < pods_total:
            unhealthy_sample_count += 1
        for workload in data.get("workloads", []):
            ready = bool(workload.get("ready", False))
            status = str(workload.get("status", "unknown"))
            containers_total = int(workload.get("containers_total", 0) or 0)
            containers_ready = int(workload.get("containers_ready", 0) or 0)
            unhealthy = (containers_total > 0 and containers_ready < containers_total) or status not in ("Running", "Succeeded", "unknown")
            if not ready and containers_total == 0 and status == "unknown":
                unhealthy = True
            if unhealthy:
                name = f"{workload.get('namespace', 'unknown')}/{workload.get('name', 'unknown')}"
                unhealthy_workloads[name] += 1
        restart_values.append(sum(int(w.get("restart_count", 0) or 0) for w in data.get("workloads", [])))
    restart_delta = max(restart_values) - min(restart_values) if len(restart_values) >= 2 else 0
    not_ready_samples = [
        record for record in records
        if int(record.get("data", {}).get("nodes_total", 0) or 0) > int(record.get("data", {}).get("nodes_ready", 0) or 0)
    ]
    return {
        "infra_state_count": len(records),
        "node_not_ready_count": node_not_ready_count,
        "node_not_ready_minutes": round(len(not_ready_samples) * thresholds.infra_state_interval_seconds / 60, 2),
        "workload_restart_total": restart_delta,
        "unhealthy_workload_minutes": round(unhealthy_sample_count * thresholds.infra_state_interval_seconds / 60, 2),
        "not_ready_nodes": [
            {"node_id": node_id, "sample_count": count}
            for node_id, count in not_ready_nodes.most_common(5)
        ],
        "unhealthy_workloads": [
            {"workload": workload, "sample_count": count}
            for workload, count in unhealthy_workloads.most_common(5)
        ],
        "restart_delta": restart_delta,
    }


def _node_label(node: dict) -> str:
    node_id = str(node.get("node_id") or node.get("name") or "").strip()
    if node_id:
        return node_id
    role = str(node.get("role") or "unknown-role").strip()
    status = str(node.get("status") or "unknown-status").strip()
    return f"{role}:{status}"


def _pipeline_summary(records_by_dataset: dict[str, list[dict]], thresholds: AggregateThresholds, data_quality: dict) -> dict:
    warning_seconds = 0
    critical_seconds = 0
    for dataset in DATASETS:
        records = records_by_dataset[dataset]
        interval = thresholds.infra_state_interval_seconds if dataset == "infra_state" else thresholds.factory_state_interval_seconds
        for record in records:
            status = record.get("pipeline_status", {}).get("status")
            if status == "critical":
                critical_seconds += interval
            elif status == "warning":
                warning_seconds += interval
    return {
        "pipeline_warning_minutes": round(warning_seconds / 60, 2),
        "pipeline_critical_minutes": round(critical_seconds / 60, 2),
        "max_gap_seconds": data_quality["max_gap_seconds"],
    }


def _snapshot_summary(records: list[dict]) -> dict:
    if not records:
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
    final = records[-1]
    infra = final.get("infra_state", {})
    risk = final.get("risk", {})
    pipeline = final.get("pipeline_status", {})
    return {
        "state_snapshot_count": len(records),
        "final_updated_at": final.get("updated_at") or final.get("processed_at"),
        "last_factory_state_at": final.get("last_factory_state_at"),
        "last_infra_state_at": final.get("last_infra_state_at"),
        "final_risk_score": risk.get("score"),
        "final_risk_level": risk.get("level"),
        "final_pipeline_status": pipeline.get("status"),
        "final_nodes_ready": infra.get("nodes_ready"),
        "final_nodes_total": infra.get("nodes_total"),
        "final_pods_ready": infra.get("pods_ready"),
        "final_pods_total": infra.get("pods_total"),
    }


def _events(summary: dict, normalized: dict[str, list[dict]], thresholds: AggregateThresholds, timezone_name: str) -> list[dict]:
    events = []
    risk_events = threshold_windows(
        [
            {"timestamp": record["_timestamp"], "message_id": record["_message_id"], "score": record.get("risk", {}).get("score")}
            for record in normalized["risk_score"]
        ],
        lambda sample: float(sample.get("score") or 100) <= thresholds.risk_warning_score_max,
        thresholds.risk_score_interval_seconds,
        timezone_name,
        "risk_degradation",
        "warning",
        "Risk Score dropped below warning threshold",
        lambda items: round((100 - min(float(item.get("score") or 100) for item in items)) / 2, 2),
    )
    events.extend(risk_events)
    temp_events = threshold_windows(
        [
            {"timestamp": record["_timestamp"], "message_id": record["_message_id"], **record.get("data", {})}
            for record in normalized["factory_state"]
        ],
        lambda sample: float(sample.get("temperature_celsius") or 0) >= thresholds.temperature_warning_c,
        thresholds.factory_state_interval_seconds,
        timezone_name,
        "sensor_threshold_exceeded",
        "warning",
        "Temperature exceeded warning threshold",
        lambda items: round(max(float(item.get("temperature_celsius") or 0) for item in items) - thresholds.temperature_warning_c, 2),
    )
    events.extend(temp_events)
    events.extend(summary["factory_state"]["spike_events"])

    infra_samples = [
        {
            "timestamp": record["_timestamp"],
            "message_id": record["_message_id"],
            "nodes_total": int(record.get("data", {}).get("nodes_total", 0) or 0),
            "nodes_ready": int(record.get("data", {}).get("nodes_ready", 0) or 0),
        }
        for record in normalized["infra_state"]
    ]
    events.extend(threshold_windows(
        infra_samples,
        lambda sample: sample["nodes_total"] > sample["nodes_ready"],
        thresholds.infra_state_interval_seconds,
        timezone_name,
        "node_not_ready",
        "warning",
        "Node not ready state detected",
        lambda items: max(item["nodes_total"] - item["nodes_ready"] for item in items) * 5,
    ))
    workload_samples = [
        {
            "timestamp": record["_timestamp"],
            "message_id": record["_message_id"],
            "pods_total": int(record.get("data", {}).get("pods_total", 0) or 0),
            "pods_ready": int(record.get("data", {}).get("pods_ready", 0) or 0),
        }
        for record in normalized["infra_state"]
    ]
    events.extend(threshold_windows(
        workload_samples,
        lambda sample: sample["pods_total"] > sample["pods_ready"],
        thresholds.infra_state_interval_seconds,
        timezone_name,
        "workload_unhealthy",
        "warning",
        "Workload unhealthy state detected",
        lambda items: max(item["pods_total"] - item["pods_ready"] for item in items) * 5,
    ))
    if summary["infra"]["workload_restart_total"] > 0:
        last_infra = normalized["infra_state"][-1] if normalized["infra_state"] else None
        events.append({
            "time_range": _single_time_range(last_infra["_timestamp"], timezone_name) if last_infra else f"hh={summary['hour']}",
            "severity": "warning",
            "type": "workload_unhealthy",
            "summary": "Workload restart count increased",
            "duration_seconds": 0,
            "magnitude": summary["infra"]["workload_restart_total"] * 5,
            "evidence": {"evidence_message_ids": [last_infra["_message_id"]] if last_infra else []},
        })
    return top_events(events, thresholds.max_hourly_events)


def _duration_seconds(records: list[dict], interval_seconds: int, predicate) -> int:
    return sum(interval_seconds for record in records if predicate(record))


def _sample_duration_seconds(samples: list[dict], interval_seconds: int, predicate) -> int:
    return sum(interval_seconds for sample in samples if predicate(sample))


def _risk_level(record: dict, thresholds: AggregateThresholds) -> str:
    risk = record.get("risk", {})
    if risk.get("level") in ("safe", "normal", "warning", "danger"):
        level = risk["level"]
        return "safe" if level == "normal" else level
    score = float(risk.get("score", 100))
    if score <= thresholds.risk_danger_score_max:
        return "danger"
    if score <= thresholds.risk_warning_score_max:
        return "warning"
    return "safe"


def _rename_score_stats(stats: dict) -> dict:
    return {
        "avg_score": stats["score_avg"],
        "min_score": stats["score_min"],
        "max_score": stats["score_max"],
        "p05_score": stats["score_p05"],
        "p95_score": stats["score_p95"],
    }


def _single_time_range(timestamp, timezone_name: str) -> str:
    from report_generator.time_window import format_hhmm_range

    return format_hhmm_range(timestamp, timestamp, timezone_name)
