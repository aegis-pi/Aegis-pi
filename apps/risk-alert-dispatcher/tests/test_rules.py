import json
from pathlib import Path

from alert_dispatcher.rules import evaluate
from alert_dispatcher.snapshot_parser import parse_source


SAMPLES_DIR = Path("/tmp/aegis-processed-samples")


def test_safe_factory_state_snapshot_is_skipped():
    snapshot = _load_or_default("factory-c-state-snapshot.json", _safe_factory_snapshot())
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=01/x.json")

    assert evaluate(source, snapshot) == []


def test_factory_danger_alert_uses_top_cause_fingerprint():
    snapshot = _safe_factory_snapshot()
    snapshot["risk"] = {
        "score": 0,
        "level": "danger",
        "top_causes": [
            {
                "field": "node_status",
                "reason": "nodes_all_not_ready",
                "value": "0/2",
                "contribution": 50,
                "severity": "danger",
            }
        ],
        "gates": [],
        "calculated_at": "2026-06-02T02:00:00.000Z",
    }
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)

    assert any(alert.pk == "ALERT#factory-c" for alert in alerts)
    assert any(alert.sk == "danger#nodes_all_not_ready#normal" for alert in alerts)


def test_cloud_fast_normal_sample_is_skipped():
    snapshot = _load_or_default("cloud-infra-fast.json", _normal_fast_snapshot())
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    assert evaluate(source, snapshot) == []


def test_cloud_fast_lambda_error_alerts():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["data_pipeline"]["lambdas"][0]["errors_5m"] = 1
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)

    assert len(alerts) == 1
    assert alerts[0].pk == "ALERT#cloud-infra"
    assert alerts[0].sk == "warning#data_pipeline_lambda_errors#fast"


def test_cloud_slow_kubernetes_unauthorized_sample_is_warning():
    snapshot = _load_or_default("cloud-infra-slow.json", _unauthorized_slow_snapshot())
    source = parse_source("processed/cloud_infra/slow/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)
    keys = {alert.sk for alert in alerts}

    assert len(alerts) == 1
    assert "warning#kubernetes_api_unauthorized#slow" in keys


def test_cloud_slow_collector_error_keeps_independent_storage_alert():
    snapshot = _unauthorized_slow_snapshot()
    snapshot["slow"]["storage_freshness"] = {"status": "warning"}
    source = parse_source("processed/cloud_infra/slow/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)
    keys = {alert.sk for alert in alerts}

    assert keys == {
        "warning#kubernetes_api_unauthorized#slow",
        "warning#storage_freshness_warning#slow",
    }


def _load_or_default(name: str, default: dict) -> dict:
    path = SAMPLES_DIR / name
    if path.exists():
        return json.loads(path.read_text())
    return default


def _safe_factory_snapshot() -> dict:
    return {
        "factory_id": "factory-c",
        "updated_at": "2026-06-02T02:00:00.000Z",
        "pipeline_status": {"status": "normal"},
        "risk": {"score": 100, "level": "safe", "top_causes": [], "gates": []},
    }


def _normal_fast_snapshot() -> dict:
    return {
        "snapshot_type": "fast",
        "updated_at": "2026-06-02T02:00:00.000Z",
        "fast_updated_at": "2026-06-02T02:00:00.000Z",
        "fast": {
            "backend_runtime": {"status": "normal", "alb": {"unhealthy_host_count": 0}},
            "data_pipeline": {
                "status": "normal",
                "lambdas": [{"name": "AEGIS-Lambda-DataProcessor", "errors_5m": 0, "throttles_5m": 0}],
                "dynamodb": {"read_throttle_events_5m": 0, "write_throttle_events_5m": 0},
            },
            "factory_freshness": {"status": "normal"},
            "errors": [],
        },
    }


def _unauthorized_slow_snapshot() -> dict:
    return {
        "snapshot_type": "slow",
        "updated_at": "2026-06-02T02:00:00.000Z",
        "slow_updated_at": "2026-06-02T02:00:00.000Z",
        "slow": {
            "eks_management": {
                "status": "unknown",
                "cluster": {"status": "ACTIVE"},
                "nodegroups": [{"status": "ACTIVE"}],
                "autoscaling": {"desired_capacity": 2, "healthy_instances": 2},
                "nodes": {"status": "unknown"},
                "pods": {"status": "unknown"},
                "argocd": {"status": "unknown"},
            },
            "storage_freshness": {"status": "normal"},
            "errors": [{"collector": "kubernetes_api", "error": "HTTP 401 Unauthorized"}],
        },
    }
