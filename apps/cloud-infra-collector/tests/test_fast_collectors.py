from cloud_infra.fast_collectors import _alb_status, _ecs_status, _factory_summary, _scheduler_status


def test_backend_status_helpers():
    config = {
        "ecs_cpu_warning_percent": 85.0,
        "ecs_memory_warning_percent": 85.0,
        "alb_latency_warning_seconds": 1.0,
    }

    assert _ecs_status({"desired_count": 1, "running_count": 0}, config) == "critical"
    assert _ecs_status({"desired_count": 2, "running_count": 1}, config) == "warning"
    assert _ecs_status({"desired_count": 1, "running_count": 1, "cpu_utilization_max": 90}, config) == "warning"
    assert _ecs_status({"desired_count": 1, "running_count": 1}, config) == "normal"

    assert _alb_status({"healthy_host_count": 0}, config) == "critical"
    assert _alb_status({"healthy_host_count": 1, "target_5xx_count_5m": 1}, config) == "warning"
    assert _alb_status({"healthy_host_count": 1, "target_response_time_p95": 1.2}, config) == "warning"
    assert _alb_status({"healthy_host_count": 1}, config) == "normal"


def test_scheduler_and_factory_summary():
    assert _scheduler_status([{"state": "ENABLED"}]) == "normal"
    assert _scheduler_status([{"state": "DISABLED"}]) == "warning"

    summary = _factory_summary(
        "factory-a",
        {
            "last_infra_state_at": "2026-06-01T15:29:00Z",
            "pipeline_status": {"status": "critical", "latest_infra_state_age_seconds": 360},
            "risk": {"score": 0, "level": "danger", "top_causes": [{"field": "data_freshness"}]},
        },
    )
    assert summary["factory_id"] == "factory-a"
    assert summary["pipeline_status"] == "critical"
    assert summary["risk_level"] == "danger"

