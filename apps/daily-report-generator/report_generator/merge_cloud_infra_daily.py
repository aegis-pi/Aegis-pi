from __future__ import annotations

from collections import Counter

from report_generator.severity import top_events


def merge_cloud_infra_daily(
    target_id: str,
    report_date: str,
    timezone: str,
    hourly_summaries: list[dict],
    output_prefix: str,
    max_context_events: int = 10,
) -> dict:
    ordered = sorted(hourly_summaries, key=lambda item: item.get("hour", ""))
    events = top_events([event for summary in ordered for event in summary.get("events", [])], max_context_events)
    daily_summary = {
        "schema_version": "0.1.0",
        "summary_type": "cloud_infra_daily",
        "target_id": target_id,
        "report_date": report_date,
        "timezone": timezone,
        "report_window": _report_window(ordered, timezone),
        "overall_status": _overall_status(ordered, events),
        "data_quality": _merge_data_quality(ordered),
        "backend_runtime": _merge_backend_runtime(ordered),
        "data_pipeline": _merge_data_pipeline(ordered),
        "eks_management": _merge_eks_management(ordered),
        "argocd": _merge_argocd(ordered),
        "freshness": _merge_freshness(ordered),
        "events": events,
        "recommended_checks": _recommended_checks(events),
        "data_limitations": [
            "Report is based on S3 processed cloud_infra fast/slow snapshots, not S3 raw payloads.",
            "fast/slow prefixes are collector trigger trees; each object body is treated as an integrated cloud infra snapshot.",
            "LLM output is an operational draft and requires operator review.",
        ],
    }
    report_context = build_cloud_infra_report_context(daily_summary, max_context_events)
    return {
        "target_id": target_id,
        "report_date": report_date,
        "status": "success",
        "daily_summary": daily_summary,
        "report_context": report_context,
        "daily_summary_key": f"{output_prefix}/cloud-infra-daily-summary.json",
        "context_key": f"{output_prefix}/report-context.json",
    }


def build_cloud_infra_report_context(daily_summary: dict, max_context_events: int) -> dict:
    return {
        "schema_version": daily_summary["schema_version"],
        "context_type": "daily_cloud_infra_report",
        "target_id": daily_summary["target_id"],
        "report_date": daily_summary["report_date"],
        "timezone": daily_summary["timezone"],
        "report_window": daily_summary["report_window"],
        "overall_status": daily_summary["overall_status"],
        "data_quality": daily_summary["data_quality"],
        "backend_runtime": daily_summary["backend_runtime"],
        "data_pipeline": daily_summary["data_pipeline"],
        "eks_management": daily_summary["eks_management"],
        "argocd": daily_summary["argocd"],
        "freshness": daily_summary["freshness"],
        "events": daily_summary["events"][:max_context_events],
        "recommended_checks": daily_summary["recommended_checks"],
        "data_limitations": daily_summary["data_limitations"],
    }


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


def _merge_data_quality(summaries: list[dict]) -> dict:
    expected_fast = sum(summary.get("data_quality", {}).get("fast_expected_count", 0) or 0 for summary in summaries)
    actual_fast = sum(summary.get("data_quality", {}).get("fast_actual_count", 0) or 0 for summary in summaries)
    expected_slow = sum(summary.get("data_quality", {}).get("slow_expected_count", 0) or 0 for summary in summaries)
    actual_slow = sum(summary.get("data_quality", {}).get("slow_actual_count", 0) or 0 for summary in summaries)
    gap_windows = [
        {**window, "hour": summary.get("hour")}
        for summary in summaries
        for window in summary.get("data_quality", {}).get("gap_windows", [])
    ]
    gap_windows.sort(key=lambda item: item.get("duration_seconds", 0), reverse=True)
    non_empty_hours = [
        summary.get("hour")
        for summary in summaries
        if (summary.get("data_quality", {}).get("fast_actual_count", 0) or 0) > 0
        or (summary.get("data_quality", {}).get("slow_actual_count", 0) or 0) > 0
    ]
    empty_tail_hour_count = _empty_tail_hour_count(summaries)
    return {
        "fast_expected_count": expected_fast,
        "fast_actual_count": actual_fast,
        "fast_collection_rate": _rate(actual_fast, expected_fast),
        "slow_expected_count": expected_slow,
        "slow_actual_count": actual_slow,
        "slow_collection_rate": _rate(actual_slow, expected_slow),
        "missing_hour_count": 24 - len({summary.get("hour") for summary in summaries}),
        "latest_observed_hour": non_empty_hours[-1] if non_empty_hours else None,
        "empty_tail_hour_count": empty_tail_hour_count,
        "max_gap_minutes": round(max((window.get("duration_seconds", 0) for window in gap_windows), default=0) / 60, 2),
        "gap_windows": gap_windows[:10],
        "invalid_record_count": sum(summary.get("data_quality", {}).get("invalid_record_count", 0) or 0 for summary in summaries),
        "duplicate_record_count": sum(summary.get("data_quality", {}).get("duplicate_record_count", 0) or 0 for summary in summaries),
    }


def _empty_tail_hour_count(summaries: list[dict]) -> int:
    count = 0
    for summary in reversed(sorted(summaries, key=lambda item: item.get("hour", ""))):
        quality = summary.get("data_quality", {})
        if (quality.get("fast_actual_count", 0) or 0) > 0 or (quality.get("slow_actual_count", 0) or 0) > 0:
            break
        count += 1
    return count


def _merge_backend_runtime(summaries: list[dict]) -> dict:
    items = [summary.get("backend_runtime", {}) for summary in summaries]
    return {
        "ecs_desired_count": _last(items, "ecs_desired_count"),
        "ecs_running_count_min": _min(items, "ecs_running_count_min"),
        "ecs_running_count_max": _max(items, "ecs_running_count_max"),
        "ecs_pending_count_max": _max(items, "ecs_pending_count_max"),
        "ecs_cpu_avg": _avg(items, "ecs_cpu_avg"),
        "ecs_cpu_max": _max(items, "ecs_cpu_max"),
        "ecs_memory_avg": _avg(items, "ecs_memory_avg"),
        "ecs_memory_max": _max(items, "ecs_memory_max"),
        "alb_healthy_host_min": _min(items, "alb_healthy_host_min"),
        "alb_unhealthy_host_max": _max(items, "alb_unhealthy_host_max"),
        "alb_5xx_total": _sum(items, "alb_5xx_total"),
    }


def _merge_data_pipeline(summaries: list[dict]) -> dict:
    items = [summary.get("data_pipeline", {}) for summary in summaries]
    return {
        "lambda_error_total": _sum(items, "lambda_error_total"),
        "lambda_throttle_total": _sum(items, "lambda_throttle_total"),
        "lambda_duration_p95_max": _max(items, "lambda_duration_p95_max"),
        "dynamodb_read_throttle_total": _sum(items, "dynamodb_read_throttle_total"),
        "dynamodb_write_throttle_total": _sum(items, "dynamodb_write_throttle_total"),
        "dynamodb_system_error_total": _sum(items, "dynamodb_system_error_total"),
        "disabled_scheduler_count": _max(items, "disabled_scheduler_count") or 0,
    }


def _merge_eks_management(summaries: list[dict]) -> dict:
    items = [summary.get("eks_management", {}) for summary in summaries]
    return {
        "cluster_status": _cluster_status(items),
        "nodes_ready_min": _min(items, "nodes_ready_min"),
        "nodes_total_max": _max(items, "nodes_total_max"),
        "not_ready_node_minutes": _sum(items, "not_ready_node_minutes"),
        "pod_pending_max": _max(items, "pod_pending_max"),
        "pod_failed_max": _max(items, "pod_failed_max"),
        "pod_unknown_max": _max(items, "pod_unknown_max"),
        "restart_count_delta": _sum(items, "restart_count_delta"),
        "top_cpu_pods": _top_pods(items, "top_cpu_pods"),
        "top_memory_pods": _top_pods(items, "top_memory_pods"),
    }


def _merge_argocd(summaries: list[dict]) -> dict:
    items = [summary.get("argocd", {}) for summary in summaries]
    return {
        "applications_total_max": _max(items, "applications_total_max"),
        "synced_min": _min(items, "synced_min"),
        "out_of_sync_max": _max(items, "out_of_sync_max"),
        "degraded_max": _max(items, "degraded_max"),
        "healthy_min": _min(items, "healthy_min"),
    }


def _merge_freshness(summaries: list[dict]) -> dict:
    items = [summary.get("freshness", {}) for summary in summaries]
    return {
        "factory_pipeline_warning_minutes": _sum(items, "factory_pipeline_warning_minutes"),
        "factory_pipeline_critical_minutes": _sum(items, "factory_pipeline_critical_minutes"),
        "stale_factory_count_max": _max(items, "stale_factory_count_max") or 0,
        "storage_freshness_non_normal_count": _max(items, "storage_freshness_non_normal_count") or 0,
    }


def _overall_status(summaries: list[dict], events: list[dict]) -> str:
    statuses = [str(summary.get("overall_status", "")).lower() for summary in summaries if summary.get("overall_status")]
    if any(event.get("severity") == "danger" for event in events):
        return "danger"
    if any(status not in ("normal", "ok", "healthy") for status in statuses) or events:
        return "warning"
    return "normal"


def _recommended_checks(events: list[dict]) -> list[dict]:
    labels = {
        "cloud_fast_collection_gap": "Cloud infra fast collection gap review",
        "cloud_slow_collection_gap": "Cloud infra slow collection gap review",
        "backend_ecs_capacity_mismatch": "Backend ECS desired/running capacity review",
        "backend_alb_unhealthy": "Backend ALB target health review",
        "backend_alb_5xx": "Backend ALB 5xx request trace review",
        "pipeline_lambda_error": "Data Pipeline Lambda error log review",
        "pipeline_lambda_throttle": "Data Pipeline Lambda throttle review",
        "dynamodb_throttle_or_error": "DynamoDB throttle and system error review",
        "scheduler_disabled": "EventBridge Scheduler state review",
        "eks_cluster_non_active": "EKS cluster status review",
        "eks_node_not_ready": "EKS node readiness review",
        "eks_pod_unhealthy": "EKS pod health review",
        "eks_pod_restart_increase": "EKS pod restart review",
        "argocd_out_of_sync": "ArgoCD sync status review",
        "argocd_degraded": "ArgoCD degraded application review",
        "factory_freshness_stale": "Factory freshness stale pipeline review",
        "storage_freshness_stale": "Storage freshness stale data review",
    }
    checks = []
    seen = set()
    for event in events:
        event_type = event.get("type")
        if event_type in seen:
            continue
        seen.add(event_type)
        checks.append({
            "priority": "high" if event.get("severity") == "danger" else "medium",
            "item": labels.get(event_type, event_type),
            "reason": event.get("summary"),
            "event_type": event_type,
            "time_range": event.get("time_range"),
            "evidence": event.get("evidence", {}),
        })
    return checks[:10]


def _top_pods(items: list[dict], key: str) -> list[dict]:
    pods = [pod for item in items for pod in item.get(key, [])]
    return sorted(pods, key=lambda item: item.get("value", item.get("usage", 0)) or 0, reverse=True)[:5]


def _values(items: list[dict], key: str) -> list[float]:
    return [float(item[key]) for item in items if isinstance(item.get(key), (int, float))]


def _sum(items: list[dict], key: str):
    return int(sum(_values(items, key)))


def _min(items: list[dict], key: str):
    values = _values(items, key)
    return min(values) if values else None


def _max(items: list[dict], key: str):
    values = _values(items, key)
    return max(values) if values else None


def _avg(items: list[dict], key: str):
    values = _values(items, key)
    return round(sum(values) / len(values), 2) if values else None


def _last(items: list[dict], key: str):
    for item in reversed(items):
        if item.get(key) is not None:
            return item[key]
    return None


def _cluster_status(items: list[dict]):
    statuses = [item.get("cluster_status") for item in items if item.get("cluster_status")]
    for status in statuses:
        if str(status).upper() != "ACTIVE":
            return status
    return statuses[-1] if statuses else None


def _rate(actual: int, expected: int) -> float:
    return round(actual / expected, 4) if expected else 0
