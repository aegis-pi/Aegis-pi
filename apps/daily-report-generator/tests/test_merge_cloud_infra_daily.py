from report_generator.merge_cloud_infra_daily import merge_cloud_infra_daily


def test_merge_cloud_infra_daily_builds_context_and_recommended_checks():
    hourly = [_summary("00"), _summary("01")]
    hourly[1]["backend_runtime"]["alb_5xx_total"] = 4
    hourly[1]["events"] = [
        {
            "type": "backend_alb_5xx",
            "severity": "warning",
            "summary": "ALB 5xx responses were observed",
            "time_range": "01:00~01:59",
            "duration_seconds": 3600,
            "magnitude": 4,
        }
    ]

    result = merge_cloud_infra_daily(
        target_id="cloud-infra",
        report_date="2026-01-01",
        timezone="Asia/Seoul",
        hourly_summaries=hourly,
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra",
    )

    assert result["daily_summary_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra/cloud-infra-daily-summary.json"
    assert result["context_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra/report-context.json"
    context = result["report_context"]
    assert context["context_type"] == "daily_cloud_infra_report"
    assert context["target_id"] == "cloud-infra"
    assert context["overall_status"] == "warning"
    assert context["data_quality"]["fast_expected_count"] == 120
    assert context["data_quality"]["fast_actual_count"] == 118
    assert context["data_quality"]["fast_collection_rate"] == 0.9833
    assert context["data_quality"]["missing_hour_count"] == 22
    assert context["data_quality"]["latest_observed_hour"] == "01"
    assert context["data_quality"]["empty_tail_hour_count"] == 0
    assert context["backend_runtime"]["alb_5xx_total"] == 4
    assert context["eks_management"]["nodes_ready_min"] == 2
    assert context["argocd"]["synced_min"] == 3
    assert context["recommended_checks"][0]["item"] == "Backend ALB 5xx request trace review"


def _summary(hour):
    return {
        "summary_type": "cloud_infra_hour",
        "target_id": "cloud-infra",
        "report_date": "2026-01-01",
        "timezone": "Asia/Seoul",
        "hour": hour,
        "hour_window": {
            "start_kst": f"2026-01-01T{hour}:00:00+09:00",
            "end_kst": f"2026-01-01T{hour}:59:59+09:00",
            "start_utc": f"2025-12-31T{int(hour) + 15:02d}:00:00Z",
            "end_utc": f"2025-12-31T{int(hour) + 15:02d}:59:59Z",
        },
        "overall_status": "normal",
        "data_quality": {
            "fast_expected_count": 60,
            "fast_actual_count": 59,
            "fast_collection_rate": 0.9833,
            "slow_expected_count": 12,
            "slow_actual_count": 12,
            "slow_collection_rate": 1.0,
            "max_gap_minutes": 0,
            "gap_windows": [],
            "invalid_record_count": 0,
            "duplicate_record_count": 0,
        },
        "backend_runtime": {
            "ecs_desired_count": 2,
            "ecs_running_count_min": 2,
            "ecs_running_count_max": 2,
            "ecs_pending_count_max": 0,
            "ecs_cpu_avg": 30,
            "ecs_cpu_max": 35,
            "ecs_memory_avg": 50,
            "ecs_memory_max": 55,
            "alb_healthy_host_min": 2,
            "alb_unhealthy_host_max": 0,
            "alb_5xx_total": 0,
        },
        "data_pipeline": {
            "lambda_error_total": 0,
            "lambda_throttle_total": 0,
            "lambda_duration_p95_max": 120,
            "dynamodb_read_throttle_total": 0,
            "dynamodb_write_throttle_total": 0,
            "dynamodb_system_error_total": 0,
            "disabled_scheduler_count": 0,
        },
        "eks_management": {
            "cluster_status": "ACTIVE",
            "nodes_ready_min": 2,
            "nodes_total_max": 2,
            "not_ready_node_minutes": 0,
            "pod_pending_max": 0,
            "pod_failed_max": 0,
            "pod_unknown_max": 0,
            "restart_count_delta": 0,
        },
        "argocd": {
            "applications_total_max": 3,
            "synced_min": 3,
            "out_of_sync_max": 0,
            "degraded_max": 0,
            "healthy_min": 3,
        },
        "freshness": {
            "factory_pipeline_warning_minutes": 0,
            "factory_pipeline_critical_minutes": 0,
            "stale_factory_count_max": 0,
            "storage_freshness_non_normal_count": 0,
        },
        "events": [],
    }
