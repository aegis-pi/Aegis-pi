from datetime import datetime, timezone

from cloud_infra import fast_collectors
from cloud_infra.fast_collectors import (
    _alb_status,
    _alb_summary,
    _ecs_status,
    _ecs_summary,
    _factory_summary,
    _scheduler_status,
)


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
    assert _alb_status({"target_group_name": "missing-tg", "status": "unknown"}, config) == "critical"


def test_ecs_summary_excludes_load_balancers(monkeypatch):
    ecs = _FakeEcsClient()
    monkeypatch.setattr(fast_collectors, "_boto3_client", lambda service: ecs)

    summary = _ecs_summary({
        "ecs_cluster_name": "cluster",
        "ecs_service_name": "service",
    })

    assert "load_balancers" not in summary


def test_alb_summary_uses_configured_target_group_name(monkeypatch):
    elbv2 = _FakeElbv2Client()
    monkeypatch.setattr(fast_collectors, "_boto3_client", lambda service: elbv2)
    monkeypatch.setattr(fast_collectors, "_get_metric_values", lambda queries, now, minutes: {})

    summary = _alb_summary(
        {"target_group_name": "configured-name", "metric_window_minutes": 5},
        datetime(2026, 6, 4, tzinfo=timezone.utc),
    )

    assert elbv2.target_group_calls == [{"Names": ["configured-name"]}]
    assert summary["target_group_name"] == "configured-name"
    assert summary["target_group_arn"] == _TARGET_GROUP_ARN
    assert summary["healthy_host_count"] == 1
    assert summary["unhealthy_host_count"] == 3


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


class _FakeEcsClient:
    def describe_services(self, cluster, services):
        return {
            "services": [{
                "status": "ACTIVE",
                "desiredCount": 2,
                "runningCount": 2,
                "pendingCount": 0,
                "loadBalancers": [{"targetGroupArn": _TARGET_GROUP_ARN}],
            }],
        }


class _FakeElbv2Client:
    def __init__(self):
        self.target_group_calls = []

    def describe_target_groups(self, **kwargs):
        self.target_group_calls.append(kwargs)
        return {
            "TargetGroups": [{
                "TargetGroupArn": _TARGET_GROUP_ARN,
                "TargetGroupName": "current-name",
                "LoadBalancerArns": [_LOAD_BALANCER_ARN],
            }],
        }

    def describe_target_health(self, TargetGroupArn):
        return {
            "TargetHealthDescriptions": [
                {"TargetHealth": {"State": "healthy"}},
                {"TargetHealth": {"State": "unhealthy"}},
                {"TargetHealth": {"State": "draining"}},
                {"TargetHealth": {"State": "initial"}},
            ],
        }


_TARGET_GROUP_ARN = "arn:aws:elasticloadbalancing:ap-south-1:123456789012:targetgroup/current-name/abc123"
_LOAD_BALANCER_ARN = "arn:aws:elasticloadbalancing:ap-south-1:123456789012:loadbalancer/app/current-alb/def456"
