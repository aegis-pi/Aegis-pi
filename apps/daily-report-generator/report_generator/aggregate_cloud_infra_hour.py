from __future__ import annotations

from statistics import mean

from report_generator.severity import top_events
from report_generator.time_window import format_hhmm_range, parse_timestamp, parse_window_bound


FAST_EXPECTED_COUNT = 60
SLOW_EXPECTED_COUNT = 12


def aggregate_cloud_infra_hour_records(
    target_id: str,
    report_date: str,
    timezone: str,
    hour: str,
    hour_window: dict,
    records_by_stream: dict[str, list[dict]],
    output_prefix: str | None = None,
) -> dict:
    start = parse_window_bound(hour_window["start_kst"])
    end = _exclusive_end(parse_window_bound(hour_window["end_kst"]))
    normalized = {}
    invalid_count = 0
    duplicate_count = 0
    for stream in ("fast", "slow"):
        records, invalid, duplicate = _valid_unique_records(records_by_stream.get(stream, []), start, end)
        normalized[stream] = records
        invalid_count += invalid
        duplicate_count += duplicate

    latest = _latest_snapshot([record for records in normalized.values() for record in records])
    summary = {
        "schema_version": "0.1.0",
        "summary_type": "cloud_infra_hour",
        "target_id": target_id,
        "report_date": report_date,
        "timezone": timezone,
        "hour": hour,
        "hour_window": hour_window,
        "status": "empty" if not normalized["fast"] and not normalized["slow"] else "success",
        "data_quality": _data_quality(normalized, start, end, timezone, invalid_count, duplicate_count),
        "backend_runtime": _backend_runtime(normalized["fast"]),
        "data_pipeline": _data_pipeline(normalized["fast"]),
        "eks_management": _eks_management(normalized["slow"]),
        "argocd": _argocd(normalized["slow"]),
        "freshness": _freshness(normalized),
        "overall_status": latest.get("overall_status"),
    }
    summary["events"] = _events(summary, normalized, timezone)
    if output_prefix:
        summary["summary_key"] = f"{output_prefix}/intermediate/hourly/hh={hour}.json"
    return summary


def _valid_unique_records(records: list[dict], start, end) -> tuple[list[dict], int, int]:
    valid = []
    seen = set()
    invalid = 0
    duplicate = 0
    for record in records:
        try:
            if record.get("schema_version") != "cloud-infra-status-v1":
                raise ValueError("invalid schema")
            timestamp = parse_timestamp(record["updated_at"])
            if timestamp < start or timestamp >= end:
                continue
            if not record.get("fast") and not record.get("slow"):
                raise ValueError("missing fast/slow")
            key = record.get("updated_at") or record.get("_s3_key")
            if not key:
                raise ValueError("missing duplicate key")
        except Exception:
            invalid += 1
            continue
        if key in seen:
            duplicate += 1
            continue
        seen.add(key)
        valid.append({**record, "_timestamp": timestamp, "_message_id": key})
    valid.sort(key=lambda item: item["_timestamp"])
    return valid, invalid, duplicate


def _exclusive_end(end):
    from datetime import timedelta

    return end + timedelta(seconds=1)


def _data_quality(records_by_stream: dict[str, list[dict]], start, end, timezone: str, invalid: int, duplicate: int) -> dict:
    gap_windows = []
    for stream, threshold_seconds in (("fast", 120), ("slow", 600)):
        gap_windows.extend(_gap_windows(stream, records_by_stream[stream], start, end, threshold_seconds, timezone))
    gap_windows.sort(key=lambda item: item["duration_seconds"], reverse=True)
    fast_actual = len(records_by_stream["fast"])
    slow_actual = len(records_by_stream["slow"])
    return {
        "fast_expected_count": FAST_EXPECTED_COUNT,
        "fast_actual_count": fast_actual,
        "fast_collection_rate": _rate(fast_actual, FAST_EXPECTED_COUNT),
        "slow_expected_count": SLOW_EXPECTED_COUNT,
        "slow_actual_count": slow_actual,
        "slow_collection_rate": _rate(slow_actual, SLOW_EXPECTED_COUNT),
        "max_gap_minutes": round(max((gap["duration_seconds"] for gap in gap_windows), default=0) / 60, 2),
        "gap_windows": gap_windows[:10],
        "invalid_record_count": invalid,
        "duplicate_record_count": duplicate,
    }


def _gap_windows(stream: str, records: list[dict], start, end, threshold_seconds: int, timezone: str) -> list[dict]:
    if not records:
        return [_gap_window(stream, start, end, "hour_empty", timezone)]
    windows = []
    first = records[0]["_timestamp"]
    if (first - start).total_seconds() > threshold_seconds:
        windows.append(_gap_window(stream, start, first, "hour_start", timezone))
    for left, right in zip(records, records[1:]):
        if (right["_timestamp"] - left["_timestamp"]).total_seconds() > threshold_seconds:
            windows.append(_gap_window(stream, left["_timestamp"], right["_timestamp"], "internal", timezone))
    last = records[-1]["_timestamp"]
    if (end - last).total_seconds() > threshold_seconds:
        windows.append(_gap_window(stream, last, end, "hour_end", timezone))
    return windows


def _gap_window(stream: str, start, end, gap_type: str, timezone: str) -> dict:
    duration_seconds = max(int((end - start).total_seconds()), 0)
    return {
        "stream": stream,
        "dataset": f"cloud_infra_{stream}",
        "gap_type": gap_type,
        "start_utc": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end_utc": end.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "time_range": format_hhmm_range(start, end, timezone),
        "duration_seconds": duration_seconds,
        "duration_minutes": round(duration_seconds / 60, 2),
    }


def _backend_runtime(records: list[dict]) -> dict:
    ecs_items = [_path(record, "fast", "backend_runtime", "ecs") or {} for record in records]
    alb_items = [_path(record, "fast", "backend_runtime", "alb") or {} for record in records]
    return {
        "ecs_desired_count": _last_number(ecs_items, "desired_count"),
        "ecs_running_count_min": _min_number(ecs_items, "running_count"),
        "ecs_running_count_max": _max_number(ecs_items, "running_count"),
        "ecs_pending_count_max": _max_number(ecs_items, "pending_count"),
        "ecs_cpu_avg": _avg_number(ecs_items, "cpu_percent", "cpu_utilization_avg"),
        "ecs_cpu_max": _max_number(ecs_items, "cpu_percent", "cpu_utilization_max"),
        "ecs_memory_avg": _avg_number(ecs_items, "memory_percent", "memory_utilization_avg"),
        "ecs_memory_max": _max_number(ecs_items, "memory_percent", "memory_utilization_max"),
        "alb_healthy_host_min": _min_number(alb_items, "healthy_host_count"),
        "alb_unhealthy_host_max": _max_number(alb_items, "unhealthy_host_count"),
        "alb_5xx_total": _sum_number(alb_items, "http_5xx_count"),
    }


def _data_pipeline(records: list[dict]) -> dict:
    lambdas = [item for record in records for item in _path(record, "fast", "data_pipeline", "lambdas", default=[])]
    dynamodb_items = [_path(record, "fast", "data_pipeline", "dynamodb") or {} for record in records]
    schedulers = [item for record in records for item in _path(record, "fast", "data_pipeline", "schedulers", default=[])]
    return {
        "lambda_error_total": _sum_number(lambdas, "error_count", "errors_5m"),
        "lambda_throttle_total": _sum_number(lambdas, "throttle_count", "throttles_5m"),
        "lambda_duration_p95_max": _max_number(lambdas, "duration_p95_ms"),
        "dynamodb_read_throttle_total": _sum_number(dynamodb_items, "read_throttle_count", "read_throttle_events_5m"),
        "dynamodb_write_throttle_total": _sum_number(dynamodb_items, "write_throttle_count", "write_throttle_events_5m"),
        "dynamodb_system_error_total": _sum_number(dynamodb_items, "system_error_count", "system_errors_5m"),
        "disabled_scheduler_count": sum(1 for item in schedulers if _is_disabled(item)),
    }


def _eks_management(records: list[dict]) -> dict:
    clusters = [_path(record, "slow", "eks_management", "cluster") or {} for record in records]
    nodes = [_path(record, "slow", "eks_management", "nodes") or {} for record in records]
    observed_nodes = [item for item in nodes if _positive(_first_number(item, "total_count", "total"))]
    pods = [_path(record, "slow", "eks_management", "pods") or {} for record in records]
    return {
        "cluster_status": _last_text(clusters, "status"),
        "nodes_ready_min": _min_number(observed_nodes, "ready_count", "ready"),
        "nodes_total_max": _max_number(observed_nodes, "total_count", "total"),
        "not_ready_node_minutes": sum(max((_first_number(item, "total_count", "total") or 0) - (_first_number(item, "ready_count", "ready") or 0), 0) * 5 for item in observed_nodes),
        "pod_pending_max": _max_number(pods, "pending_count", "pending"),
        "pod_failed_max": _max_number(pods, "failed_count", "failed"),
        "pod_unknown_max": _max_number(pods, "unknown_count", "unknown"),
        "restart_count_delta": _delta(pods, "restart_count", "restart_count_total"),
        "top_cpu_pods": _top_pods(records, "top_cpu_pods", "top_by_cpu"),
        "top_memory_pods": _top_pods(records, "top_memory_pods", "top_by_memory"),
    }


def _argocd(records: list[dict]) -> dict:
    items = [_path(record, "slow", "eks_management", "argocd") or {} for record in records]
    observed_items = [item for item in items if _positive(item.get("applications_total"))]
    return {
        "applications_total_max": _max_number(items, "applications_total"),
        "synced_min": _min_number(observed_items, "synced"),
        "out_of_sync_max": _max_number(items, "out_of_sync"),
        "degraded_max": _max_number(items, "degraded"),
        "healthy_min": _min_number(observed_items, "healthy"),
    }


def _freshness(records_by_stream: dict[str, list[dict]]) -> dict:
    factory_items = [item for record in records_by_stream["fast"] for item in _path(record, "fast", "factory_freshness", "factories", default=[])]
    storage_items = [item for record in records_by_stream["slow"] for item in _path(record, "slow", "storage_freshness", "factories", default=[])]
    return {
        "factory_pipeline_warning_minutes": _freshness_minutes(factory_items, "warning"),
        "factory_pipeline_critical_minutes": _freshness_minutes(factory_items, "critical"),
        "stale_factory_count_max": _max_stale_count(factory_items),
        "storage_freshness_non_normal_count": sum(1 for item in storage_items if str(item.get("status", "normal")).lower() != "normal"),
    }


def _events(summary: dict, records_by_stream: dict[str, list[dict]], timezone: str) -> list[dict]:
    events = []
    dq = summary["data_quality"]
    if summary.get("overall_status") and str(summary["overall_status"]).lower() not in ("normal", "ok", "healthy"):
        events.append(_event("cloud_overall_status_non_normal", "warning", "Cloud infra overall status was non-normal", summary["hour_window"], timezone, magnitude=5))
    for gap in dq["gap_windows"]:
        events.append({
            "type": "cloud_fast_collection_gap" if gap["stream"] == "fast" else "cloud_slow_collection_gap",
            "severity": "warning",
            "summary": f"{gap['stream']} collection gap detected",
            "time_range": gap["time_range"],
            "duration_seconds": gap["duration_seconds"],
            "magnitude": min(gap["duration_minutes"], 20),
            "evidence": {"stream": gap["stream"]},
        })
    backend = summary["backend_runtime"]
    if _positive_diff(backend.get("ecs_desired_count"), backend.get("ecs_running_count_min")):
        events.append(_event("backend_ecs_capacity_mismatch", "warning", "ECS running count was below desired count", summary["hour_window"], timezone, magnitude=5))
    if _positive(backend.get("alb_unhealthy_host_max")):
        events.append(_event("backend_alb_unhealthy", "warning", "ALB unhealthy host was observed", summary["hour_window"], timezone, magnitude=backend["alb_unhealthy_host_max"]))
    if _positive(backend.get("alb_5xx_total")):
        events.append(_event("backend_alb_5xx", "warning", "ALB 5xx responses were observed", summary["hour_window"], timezone, magnitude=backend["alb_5xx_total"]))
    pipeline = summary["data_pipeline"]
    for key, event_type in (("lambda_error_total", "pipeline_lambda_error"), ("lambda_throttle_total", "pipeline_lambda_throttle")):
        if _positive(pipeline.get(key)):
            events.append(_event(event_type, "warning", f"{key} was observed", summary["hour_window"], timezone, magnitude=pipeline[key]))
    if _positive(pipeline.get("dynamodb_read_throttle_total")) or _positive(pipeline.get("dynamodb_write_throttle_total")) or _positive(pipeline.get("dynamodb_system_error_total")):
        events.append(_event("dynamodb_throttle_or_error", "warning", "DynamoDB throttle or system error was observed", summary["hour_window"], timezone, magnitude=5))
    if _positive(pipeline.get("disabled_scheduler_count")):
        events.append(_event("scheduler_disabled", "warning", "Disabled scheduler was observed", summary["hour_window"], timezone, magnitude=pipeline["disabled_scheduler_count"]))
    eks = summary["eks_management"]
    if eks.get("cluster_status") and str(eks["cluster_status"]).upper() != "ACTIVE":
        events.append(_event("eks_cluster_non_active", "danger", "EKS cluster status was not ACTIVE", summary["hour_window"], timezone, magnitude=10))
    if _positive(eks.get("not_ready_node_minutes")):
        events.append(_event("eks_node_not_ready", "warning", "EKS node not-ready minutes were observed", summary["hour_window"], timezone, magnitude=eks["not_ready_node_minutes"] / 5))
    if _positive(eks.get("pod_pending_max")) or _positive(eks.get("pod_failed_max")) or _positive(eks.get("pod_unknown_max")):
        events.append(_event("eks_pod_unhealthy", "warning", "Unhealthy EKS pod state was observed", summary["hour_window"], timezone, magnitude=5))
    if _positive(eks.get("restart_count_delta")):
        events.append(_event("eks_pod_restart_increase", "warning", "Pod restart count increased", summary["hour_window"], timezone, magnitude=eks["restart_count_delta"]))
    argo = summary["argocd"]
    if _positive(argo.get("out_of_sync_max")):
        events.append(_event("argocd_out_of_sync", "warning", "ArgoCD out-of-sync application was observed", summary["hour_window"], timezone, magnitude=argo["out_of_sync_max"]))
    if _positive(argo.get("degraded_max")):
        events.append(_event("argocd_degraded", "warning", "ArgoCD degraded application was observed", summary["hour_window"], timezone, magnitude=argo["degraded_max"]))
    fresh = summary["freshness"]
    if _positive(fresh.get("stale_factory_count_max")):
        events.append(_event("factory_freshness_stale", "warning", "Factory freshness stale state was observed", summary["hour_window"], timezone, magnitude=fresh["stale_factory_count_max"]))
    if _positive(fresh.get("storage_freshness_non_normal_count")):
        events.append(_event("storage_freshness_stale", "warning", "Storage freshness non-normal state was observed", summary["hour_window"], timezone, magnitude=fresh["storage_freshness_non_normal_count"]))
    return top_events(events, 20)


def _event(event_type: str, severity: str, summary: str, hour_window: dict, timezone: str, magnitude: float = 0) -> dict:
    start = parse_window_bound(hour_window["start_kst"])
    end = parse_window_bound(hour_window["end_kst"])
    return {
        "type": event_type,
        "severity": severity,
        "summary": summary,
        "time_range": format_hhmm_range(start, end, timezone),
        "duration_seconds": 3600,
        "magnitude": magnitude,
        "evidence": {"hour": hour_window},
    }


def _latest_snapshot(records: list[dict]) -> dict:
    return max(records, key=lambda item: item["_timestamp"]) if records else {}


def _path(item: dict, *keys: str, default=None):
    current = item
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _values(items: list[dict], *keys: str) -> list[float]:
    values = []
    for item in items:
        value = _first_number(item, *keys)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _sum_number(items: list[dict], *keys: str):
    values = _values(items, *keys)
    return int(sum(values)) if values else 0


def _min_number(items: list[dict], *keys: str):
    values = _values(items, *keys)
    return min(values) if values else None


def _max_number(items: list[dict], *keys: str):
    values = _values(items, *keys)
    return max(values) if values else None


def _avg_number(items: list[dict], *keys: str):
    values = _values(items, *keys)
    return round(mean(values), 2) if values else None


def _last_number(items: list[dict], key: str):
    values = _values(items, key)
    return values[-1] if values else None


def _last_text(items: list[dict], key: str):
    for item in reversed(items):
        if item.get(key) is not None:
            return item[key]
    return None


def _delta(items: list[dict], *keys: str):
    values = _values(items, *keys)
    if len(values) < 2:
        return 0
    return max(int(values[-1] - values[0]), 0)


def _top_pods(records: list[dict], *keys: str) -> list[dict]:
    pods = [
        pod
        for record in records
        for key in keys
        for pod in _path(record, "slow", "eks_management", "pods", key, default=[])
    ]
    return sorted(pods, key=lambda item: item.get("value", item.get("usage", 0)) or 0, reverse=True)[:5]


def _first_number(item: dict, *keys: str):
    for key in keys:
        value = item.get(key)
        if isinstance(value, (int, float)):
            return value
    return None


def _freshness_minutes(items: list[dict], status: str) -> int:
    return sum(1 for item in items if str(item.get("status", "")).lower() == status) * 1


def _max_stale_count(items: list[dict]) -> int:
    by_sample = {}
    for item in items:
        sample = item.get("updated_at") or item.get("factory_id") or len(by_sample)
        if str(item.get("status", "normal")).lower() != "normal":
            by_sample[sample] = by_sample.get(sample, 0) + 1
    return max(by_sample.values(), default=0)


def _is_disabled(item: dict) -> bool:
    return str(item.get("state") or item.get("status") or "").upper() in ("DISABLED", "DISABLE")


def _positive(value) -> bool:
    return value is not None and value > 0


def _positive_diff(left, right) -> bool:
    return left is not None and right is not None and left > right


def _rate(actual: int, expected: int) -> float:
    return round(actual / expected, 4) if expected else 0
