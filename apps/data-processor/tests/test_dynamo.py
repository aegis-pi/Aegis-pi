from decimal import Decimal
import sys
from types import SimpleNamespace

sys.modules["boto3"] = SimpleNamespace(
    client=lambda service: None,
    resource=lambda service: None,
)
from processor import dynamo


class FakeTable:
    def __init__(self):
        self.item = {
            "pk": "FACTORY#factory-a",
            "sk": "LATEST",
            "factory_id": "factory-a",
            "infra_state": {
                "message_id": "infra-message",
                "source_timestamp": "2026-05-21T10:00:00Z",
            },
        }
        self.history_item = None

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues, ExpressionAttributeNames=None):
        self.item["pk"] = Key["pk"]
        self.item["sk"] = Key["sk"]
        self.item["updated_at"] = ExpressionAttributeValues[":u"]
        if ":fid" in ExpressionAttributeValues:
            self.item["factory_id"] = ExpressionAttributeValues[":fid"]
        if ":sv" in ExpressionAttributeValues:
            self.item["schema_version"] = ExpressionAttributeValues[":sv"]
        if ":r" in ExpressionAttributeValues:
            self.item["risk"] = ExpressionAttributeValues[":r"]
        if ":ps" in ExpressionAttributeValues:
            self.item["pipeline_status"] = ExpressionAttributeValues[":ps"]

        if ":fs" in ExpressionAttributeValues:
            self.item["factory_state"] = ExpressionAttributeValues[":fs"]
            self.item["last_factory_state_at"] = ExpressionAttributeValues[":t"]

        if ":is" in ExpressionAttributeValues:
            self.item["infra_state"] = ExpressionAttributeValues[":is"]
            self.item["last_infra_state_at"] = ExpressionAttributeValues[":t"]

        if ":lis" in ExpressionAttributeValues:
            self.item["latest_image_snapshot"] = ExpressionAttributeValues[":lis"]
            self.item["last_image_snapshot_at"] = ExpressionAttributeValues[":t"]

    def get_item(self, Key):
        return {"Item": dict(self.item)}

    def put_item(self, Item):
        self.history_item = Item


def test_write_factory_state_snapshot_copies_latest_to_history(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr(dynamo, "_table", lambda: table)
    monkeypatch.setattr(dynamo.time, "time", lambda: 1_800_000_000)

    envelope = {
        "factory_id": "factory-a",
        "schema_version": "0.1.0",
        "message_id": "factory-message",
        "source_timestamp": "2026-05-21T10:00:03Z",
    }
    normalized = {
        "temperature_celsius": 31.2,
        "humidity_percent": 62.5,
        "fire_score": 0.0,
    }
    risk = {"score": 91.43, "level": "safe", "top_causes": []}
    pipeline_status = {"status": "normal", "latest_infra_state_age_seconds": 3}

    s3_snapshot = dynamo.write_factory_state_snapshot(
        "factory-a",
        envelope,
        normalized,
        risk,
        pipeline_status,
        "2026-05-21T10:00:03.123Z",
    )

    history = table.history_item
    assert table.item["sk"] == "LATEST"
    assert history["sk"] == "HISTORY#STATE#2026-05-21T10:00:03.123Z"
    assert history["ttl"] == 1_800_007_200
    assert history["infra_state"]["message_id"] == "infra-message"
    assert history["factory_state"]["temperature_celsius"] == Decimal("31.2")
    assert history["risk"]["score"] == Decimal("91.43")
    assert history["risk"]["calculation_version"] == "risk-v0.2.0"
    assert "ttl" not in s3_snapshot
    assert s3_snapshot["sk"] == "HISTORY#STATE#2026-05-21T10:00:03.123Z"
    assert s3_snapshot["factory_state"]["temperature_celsius"] == 31.2
    assert s3_snapshot["risk"]["score"] == 91.43


def test_write_pipeline_status_snapshot_recalculates_risk_and_history(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr(dynamo, "_table", lambda: table)
    monkeypatch.setattr(dynamo.time, "time", lambda: 1_800_000_000)

    table.item["factory_state"] = {"message_id": "factory-message"}
    table.item["risk"] = {"score": Decimal("100"), "level": "safe"}
    pipeline_status = {"status": "critical", "latest_infra_state_age_seconds": 3600}
    risk = {
        "score": 49.0,
        "base_score": 90.0,
        "level": "danger",
        "base_level": "safe",
        "top_causes": [],
        "gates": [{"name": "pipeline_status_critical"}],
    }

    s3_snapshot = dynamo.write_pipeline_status_snapshot(
        "factory-a",
        pipeline_status,
        "2026-05-21T10:01:03.123Z",
        risk,
    )

    history = table.history_item
    assert table.item["sk"] == "LATEST"
    assert table.item["pipeline_status"]["status"] == "critical"
    assert table.item["risk"]["score"] == Decimal("49.0")
    assert table.item["risk"]["calculation_version"] == "risk-v0.2.0"
    assert history["sk"] == "HISTORY#STATE#2026-05-21T10:01:03.123Z"
    assert s3_snapshot["pipeline_status"]["latest_infra_state_age_seconds"] == 3600
    assert s3_snapshot["risk"]["score"] == 49


def test_write_image_snapshot_reference_updates_latest_and_history(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr(dynamo, "_table", lambda: table)
    monkeypatch.setattr(dynamo.time, "time", lambda: 1_800_000_000)

    envelope = {
        "factory_id": "factory-a",
        "schema_version": "0.1.0",
        "message_id": "factory-a:image_snapshot:worker2:2026-06-08T09:42:35Z",
        "source_timestamp": "2026-06-08T09:42:35Z",
    }
    normalized = {
        "event_type": "FALLEN",
        "content_type": "image/jpeg",
        "size_bytes": 60345,
        "sha256": "a" * 64,
        "s3_bucket": "aegis-bucket-data",
        "s3_key": "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
    }

    s3_snapshot = dynamo.write_image_snapshot_reference(
        "factory-a",
        envelope,
        normalized,
        "2026-06-08T09:42:40.123Z",
    )

    latest = table.item["latest_image_snapshot"]
    assert latest["event_type"] == "FALLEN"
    assert latest["source_timestamp"] == "2026-06-08T09:42:35Z"
    assert latest["processed_at"] == "2026-06-08T09:42:40.123Z"
    assert latest["size_bytes"] == 60345
    assert table.item["last_image_snapshot_at"] == "2026-06-08T09:42:35Z"
    assert table.history_item["latest_image_snapshot"]["s3_bucket"] == "aegis-bucket-data"
    assert s3_snapshot["latest_image_snapshot"]["s3_key"].startswith("image_snapshot/factory_id=factory-a/")
