from report_generator.aggregate_cloud_infra_hour import aggregate_cloud_infra_hour_records


def test_aggregate_cloud_infra_hour_summarizes_fast_slow_snapshot_streams():
    result = aggregate_cloud_infra_hour_records(
        target_id="cloud-infra",
        report_date="2026-01-01",
        timezone="Asia/Seoul",
        hour="00",
        hour_window=_hour_window(),
        records_by_stream={
            "fast": [
                _snapshot("2025-12-31T15:00:00Z", running=2, alb_5xx=0),
                _snapshot("2025-12-31T15:03:00Z", running=1, alb_5xx=3),
                _snapshot("2025-12-31T15:03:00Z", running=1, alb_5xx=3),
                {"schema_version": "wrong", "updated_at": "2025-12-31T15:04:00Z"},
            ],
            "slow": [
                _snapshot("2025-12-31T15:00:00Z", cluster_status="ACTIVE", ready=2, restarts=1),
                _snapshot("2025-12-31T15:15:00Z", cluster_status="ACTIVE", ready=1, restarts=4),
            ],
        },
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra",
    )

    assert result["summary_type"] == "cloud_infra_hour"
    assert result["summary_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra/intermediate/hourly/hh=00.json"
    assert result["data_quality"]["fast_expected_count"] == 60
    assert result["data_quality"]["fast_actual_count"] == 2
    assert result["data_quality"]["fast_collection_rate"] == 0.0333
    assert result["data_quality"]["slow_expected_count"] == 12
    assert result["data_quality"]["slow_actual_count"] == 2
    assert result["data_quality"]["slow_collection_rate"] == 0.1667
    assert result["data_quality"]["duplicate_record_count"] == 1
    assert result["data_quality"]["invalid_record_count"] == 1
    assert result["backend_runtime"]["ecs_desired_count"] == 2
    assert result["backend_runtime"]["ecs_running_count_min"] == 1
    assert result["backend_runtime"]["alb_5xx_total"] == 3
    assert result["eks_management"]["nodes_ready_min"] == 1
    assert result["eks_management"]["restart_count_delta"] == 3
    assert {event["type"] for event in result["events"]} >= {
        "cloud_fast_collection_gap",
        "backend_ecs_capacity_mismatch",
        "backend_alb_5xx",
        "eks_node_not_ready",
        "eks_pod_restart_increase",
    }


def _hour_window():
    return {
        "start_kst": "2026-01-01T00:00:00+09:00",
        "end_kst": "2026-01-01T00:59:59+09:00",
        "start_utc": "2025-12-31T15:00:00Z",
        "end_utc": "2025-12-31T15:59:59Z",
    }


def _snapshot(timestamp, running=2, alb_5xx=0, cluster_status="ACTIVE", ready=2, restarts=0):
    return {
        "schema_version": "cloud-infra-status-v1",
        "updated_at": timestamp,
        "overall_status": "normal",
        "fast": {
            "backend_runtime": {
                "ecs": {
                    "desired_count": 2,
                    "running_count": running,
                    "pending_count": 0,
                    "cpu_percent": 30,
                    "memory_percent": 55,
                },
                "alb": {
                    "healthy_host_count": running,
                    "unhealthy_host_count": 2 - running,
                    "http_5xx_count": alb_5xx,
                },
            },
            "data_pipeline": {
                "lambdas": [{"error_count": 0, "throttle_count": 0, "duration_p95_ms": 120}],
                "dynamodb": {"read_throttle_count": 0, "write_throttle_count": 0, "system_error_count": 0},
                "schedulers": [{"state": "ENABLED"}],
            },
            "factory_freshness": {"factories": [{"factory_id": "factory-a", "status": "normal"}]},
        },
        "slow": {
            "eks_management": {
                "cluster": {"status": cluster_status},
                "nodes": {"ready_count": ready, "total_count": 2},
                "pods": {"pending_count": 0, "failed_count": 0, "unknown_count": 0, "restart_count": restarts},
                "argocd": {"applications_total": 3, "synced": 3, "out_of_sync": 0, "degraded": 0, "healthy": 3},
            },
            "storage_freshness": {"factories": [{"factory_id": "factory-a", "status": "normal"}]},
        },
    }
