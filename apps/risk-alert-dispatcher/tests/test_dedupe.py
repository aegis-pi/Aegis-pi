import sys
from types import ModuleType, SimpleNamespace


class ClientError(Exception):
    def __init__(self, response, operation_name):
        super().__init__(response.get("Error", {}).get("Message"))
        self.response = response
        self.operation_name = operation_name


boto3 = ModuleType("boto3")
boto3.resource = lambda service: SimpleNamespace(Table=lambda name: None)
botocore = ModuleType("botocore")
botocore_exceptions = ModuleType("botocore.exceptions")
botocore_exceptions.ClientError = ClientError
sys.modules.setdefault("boto3", boto3)
sys.modules.setdefault("botocore", botocore)
sys.modules.setdefault("botocore.exceptions", botocore_exceptions)

from alert_dispatcher import dedupe
from alert_dispatcher.rules import Alert


class ScriptedTable:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def update_item(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_confirmation_waits_for_second_observation(monkeypatch):
    table = ScriptedTable([
        _conditional_failure(),
        {"Attributes": {"observation_count": 1}},
        {"Attributes": {"observation_count": 2}},
    ])
    monkeypatch.setattr(dedupe, "_table", lambda: table)

    first_result = dedupe.confirm(_alert("2026-06-04T01:00:00Z"), 1000)
    second_result = dedupe.confirm(_alert("2026-06-04T01:01:00Z"), 1060)

    assert first_result == {
        "confirmed": False,
        "observation_count": 1,
        "required_observations": 2,
        "reason": "awaiting_confirmation",
    }
    assert second_result["confirmed"] is True
    assert second_result["observation_count"] == 2
    assert table.calls[0]["Key"]["sk"].startswith("OBSERVATION#")
    assert ":zero" not in table.calls[1]["ExpressionAttributeValues"]
    assert ":window_start" not in table.calls[1]["ExpressionAttributeValues"]


def test_immediate_alert_does_not_write_confirmation_state(monkeypatch):
    table = ScriptedTable([])
    monkeypatch.setattr(dedupe, "_table", lambda: table)

    assert dedupe.confirm(_alert("2026-06-04T01:00:00Z", required=1), 1000) == {
        "confirmed": True,
        "observation_count": 1,
    }
    assert table.calls == []


def _alert(updated_at: str, required: int = 2) -> Alert:
    return Alert(
        scope="cloud-infra",
        source_type="cloud_infra_fast",
        severity="warning",
        reason="data_pipeline_lambda_errors",
        status="fast",
        source_updated_at=updated_at,
        source_key="processed/cloud_infra/fast/test.json",
        confirmation_observations=required,
        confirmation_window_seconds=90,
    )


def _conditional_failure() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "condition failed"}},
        "UpdateItem",
    )
