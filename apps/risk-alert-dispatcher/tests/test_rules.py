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
    assert any(alert.sk == "danger#nodes_all_not_ready#state_snapshot" for alert in alerts)


def test_factory_warning_without_top_cause_keeps_generic_alert():
    snapshot = _safe_factory_snapshot()
    snapshot["risk"] = {"score": 84, "level": "warning", "top_causes": [], "gates": []}
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)

    assert [alert.sk for alert in alerts] == ["warning#risk_level#state_snapshot"]


def test_factory_non_pipeline_fingerprint_ignores_pipeline_status():
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json")
    normal = _factory_warning_snapshot("normal")
    warning = _factory_warning_snapshot("warning")

    normal_keys = {alert.sk for alert in evaluate(source, normal)}
    warning_keys = {alert.sk for alert in evaluate(source, warning)}

    assert "warning#temperature_weighted_penalty#state_snapshot" in normal_keys
    assert "warning#temperature_weighted_penalty#state_snapshot" in warning_keys
    assert "warning#pipeline_status#warning" in warning_keys
    assert not any(key.endswith("#normal") for key in normal_keys)


def test_factory_warning_freshness_emits_only_pipeline_status_alert():
    snapshot = _safe_factory_snapshot()
    snapshot["pipeline_status"] = {"status": "warning", "latest_infra_state_age_seconds": 90}
    snapshot["risk"] = {
        "score": 84,
        "level": "warning",
        "top_causes": [
            {
                "field": "data_freshness",
                "reason": "pipeline_status_warning",
                "value": "warning",
                "contribution": 16,
                "severity": "warning",
            },
            {
                "field": "data_freshness",
                "reason": "data_freshness_weighted_penalty",
                "value": 90,
                "contribution": 5,
                "severity": "warning",
            },
        ],
        "gates": [{"name": "pipeline_status_warning", "level": "warning", "field": "data_freshness"}],
    }
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)

    assert [alert.sk for alert in alerts] == ["warning#pipeline_status#warning"]


def test_factory_critical_freshness_emits_only_pipeline_status_alert():
    snapshot = _safe_factory_snapshot()
    snapshot["pipeline_status"] = {"status": "critical", "latest_infra_state_age_seconds": 150}
    snapshot["risk"] = {
        "score": 49,
        "level": "danger",
        "top_causes": [
            {
                "field": "data_freshness",
                "reason": "pipeline_status_critical",
                "value": "critical",
                "contribution": 51,
                "severity": "danger",
            },
            {
                "field": "data_freshness",
                "reason": "data_freshness_weighted_penalty",
                "value": 150,
                "contribution": 10,
                "severity": "warning",
            },
        ],
        "gates": [{"name": "pipeline_status_critical", "level": "danger", "field": "data_freshness"}],
    }
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)

    assert [alert.sk for alert in alerts] == ["danger#pipeline_status#critical"]


def test_factory_pipeline_alert_keeps_independent_danger_alert():
    snapshot = _safe_factory_snapshot()
    snapshot["pipeline_status"] = {"status": "critical", "latest_infra_state_age_seconds": 150}
    snapshot["risk"] = {
        "score": 0,
        "level": "danger",
        "top_causes": [
            {
                "field": "data_freshness",
                "reason": "pipeline_status_critical",
                "value": "critical",
                "contribution": 90,
                "severity": "danger",
            },
            {
                "field": "node_status",
                "reason": "nodes_all_not_ready",
                "value": "0/2",
                "contribution": 50,
                "severity": "danger",
            },
        ],
        "gates": [
            {"name": "pipeline_status_critical", "level": "danger", "field": "data_freshness"},
            {"name": "nodes_all_not_ready", "level": "danger", "field": "node_status"},
        ],
    }
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert "danger#pipeline_status#critical" in keys
    assert "danger#nodes_all_not_ready#state_snapshot" in keys
    assert not any("data_freshness" in key or "pipeline_status_critical" in key for key in keys)


def test_cloud_fast_normal_sample_is_skipped():
    snapshot = _load_or_default("cloud-infra-fast.json", _normal_fast_snapshot())
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    assert evaluate(source, snapshot) == []


def test_cloud_fast_lambda_error_alerts():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["data_pipeline"]["status"] = "warning"
    snapshot["fast"]["data_pipeline"]["lambdas"][0]["errors_5m"] = 1
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)

    assert len(alerts) == 1
    assert alerts[0].pk == "ALERT#cloud-infra"
    assert alerts[0].sk == "warning#data_pipeline_lambda_errors#fast"
    assert alerts[0].confirmation_observations == 2
    assert alerts[0].confirmation_window_seconds == 90


def test_cloud_fast_lambda_throttle_suppresses_data_pipeline_generic():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["data_pipeline"]["status"] = "warning"
    snapshot["fast"]["data_pipeline"]["lambdas"][0]["throttles_5m"] = 1
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert keys == {"warning#data_pipeline_lambda_throttles#fast"}


def test_cloud_fast_dynamodb_throttle_suppresses_data_pipeline_generic():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["data_pipeline"]["status"] = "warning"
    snapshot["fast"]["data_pipeline"]["dynamodb"]["read_throttle_events_5m"] = 1
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert keys == {"warning#dynamodb_throttles#fast"}


def test_cloud_fast_unhealthy_host_alert_is_immediate():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["backend_runtime"]["status"] = "warning"
    snapshot["fast"]["backend_runtime"]["alb"]["unhealthy_host_count"] = 1
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)
    alert = next(alert for alert in alerts if alert.reason == "alb_unhealthy_hosts")

    assert {alert.sk for alert in alerts} == {"warning#alb_unhealthy_hosts#fast"}
    assert alert.confirmation_observations == 1


def test_cloud_fast_draining_hosts_do_not_create_alb_unhealthy_alert():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["backend_runtime"]["alb"]["draining_host_count"] = 2
    snapshot["fast"]["backend_runtime"]["alb"]["unhealthy_host_count"] = 0
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)

    assert alerts == []


def test_cloud_fast_backend_warning_without_specific_keeps_generic_fallback():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["backend_runtime"]["status"] = "warning"
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert keys == {"warning#backend_runtime_warning#fast"}


def test_cloud_fast_critical_section_uses_specific_alert_without_generic():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["backend_runtime"]["status"] = "critical"
    snapshot["fast"]["backend_runtime"]["alb"]["unhealthy_host_count"] = 2
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert keys == {"danger#alb_unhealthy_hosts#fast"}


def test_cloud_fast_factory_freshness_alert_is_skipped():
    snapshot = _normal_fast_snapshot()
    snapshot["fast"]["factory_freshness"] = {
        "status": "critical",
        "factories": [
            {
                "factory_id": "factory-c",
                "pipeline_status": "critical",
                "latest_infra_state_age_seconds": 150,
            }
        ],
    }
    source = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    assert evaluate(source, snapshot) == []


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


def test_cloud_slow_pods_warning_requires_two_observations():
    snapshot = _normal_slow_snapshot()
    snapshot["slow"]["eks_management"]["status"] = "warning"
    snapshot["slow"]["eks_management"]["pods"] = {"status": "warning", "failed": 1}
    source = parse_source("processed/cloud_infra/slow/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    alerts = evaluate(source, snapshot)
    by_reason = {alert.reason: alert for alert in alerts}

    assert set(by_reason) == {"pods_warning"}
    assert by_reason["pods_warning"].confirmation_observations == 2
    assert by_reason["pods_warning"].confirmation_window_seconds == 450


def test_cloud_slow_eks_warning_without_specific_keeps_generic_fallback():
    snapshot = _normal_slow_snapshot()
    snapshot["slow"]["eks_management"]["status"] = "warning"
    source = parse_source("processed/cloud_infra/slow/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert keys == {"warning#eks_management_warning#slow"}


def test_cloud_slow_nodes_and_pods_suppress_eks_generic_but_both_specifics_remain():
    snapshot = _normal_slow_snapshot()
    snapshot["slow"]["eks_management"]["status"] = "warning"
    snapshot["slow"]["eks_management"]["nodes"] = {"status": "warning", "not_ready": 1}
    snapshot["slow"]["eks_management"]["pods"] = {"status": "warning", "failed": 1}
    source = parse_source("processed/cloud_infra/slow/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert keys == {
        "warning#nodes_warning#slow",
        "warning#pods_warning#slow",
    }


def test_cloud_slow_pods_critical_suppresses_eks_generic():
    snapshot = _normal_slow_snapshot()
    snapshot["slow"]["eks_management"]["status"] = "critical"
    snapshot["slow"]["eks_management"]["pods"] = {"status": "critical", "failed": 2}
    source = parse_source("processed/cloud_infra/slow/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    keys = {alert.sk for alert in evaluate(source, snapshot)}

    assert keys == {"danger#pods_critical#slow"}


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


def _factory_warning_snapshot(pipeline_status: str) -> dict:
    snapshot = _safe_factory_snapshot()
    snapshot["pipeline_status"] = {"status": pipeline_status, "latest_infra_state_age_seconds": 90}
    snapshot["risk"] = {
        "score": 84,
        "level": "warning",
        "top_causes": [
            {
                "field": "temperature",
                "reason": "temperature_weighted_penalty",
                "value": 35,
                "contribution": 5,
                "severity": "warning",
            }
        ],
        "gates": [],
    }
    return snapshot


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


def _normal_slow_snapshot() -> dict:
    snapshot = _unauthorized_slow_snapshot()
    snapshot["slow"]["eks_management"].update({
        "status": "normal",
        "nodes": {"status": "normal"},
        "pods": {"status": "normal"},
        "argocd": {"status": "normal"},
    })
    snapshot["slow"]["errors"] = []
    return snapshot
