from alert_dispatcher.rules import Alert
from alert_dispatcher.slack import _secret_id_for, format_message


def test_format_factory_message_contains_required_fields():
    alert = Alert(
        scope="factory-c",
        source_type="factory_state_snapshot",
        severity="danger",
        reason="nodes_all_not_ready",
        status="normal",
        source_updated_at="2026-06-02T02:00:00.000Z",
        source_key="processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json",
        score=49,
        title="[AEGIS Alert] factory-c danger",
        summary={
            "pipeline_status": "normal",
            "top_causes": [{"field": "node_status", "reason": "nodes_all_not_ready", "value": "0/2"}],
        },
    )

    message = format_message(alert)

    assert "━━━━━━━━━━━━━━━━━━━━━━" in message
    assert "AEGIS Alert | 위험 알림" in message
    assert "무엇이 문제인가요?" in message
    assert "- 심각도: 위험(DANGER)" in message
    assert "- 위험 점수: 49" in message
    assert "- 원인: nodes_all_not_ready" in message
    assert "주요 원인" in message
    assert "항목: node_status" in message
    assert "processed/factory-c/state_snapshot/" in message


def test_webhook_secret_is_selected_by_alert_scope(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_SECRET_ID", "default-secret")
    monkeypatch.setenv("SLACK_WEBHOOK_SECRET_CLOUD", "cloud-secret")
    monkeypatch.setenv("SLACK_WEBHOOK_SECRET_FACTORY_A", "factory-a-secret")
    monkeypatch.setenv("SLACK_WEBHOOK_SECRET_FACTORY_B", "factory-b-secret")
    monkeypatch.setenv("SLACK_WEBHOOK_SECRET_FACTORY_C", "factory-c-secret")

    assert _secret_id_for(_alert("cloud-infra")) == "cloud-secret"
    assert _secret_id_for(_alert("factory-a")) == "factory-a-secret"
    assert _secret_id_for(_alert("factory-b")) == "factory-b-secret"
    assert _secret_id_for(_alert("factory-c")) == "factory-c-secret"
    assert _secret_id_for(_alert("unknown")) == "default-secret"


def _alert(scope: str) -> Alert:
    return Alert(
        scope=scope,
        source_type="factory_state_snapshot",
        severity="warning",
        reason="test",
        status="normal",
        source_updated_at="2026-06-02T02:00:00.000Z",
        source_key="processed/test.json",
    )
