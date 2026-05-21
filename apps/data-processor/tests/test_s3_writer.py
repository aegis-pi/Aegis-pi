import sys
from types import SimpleNamespace

sys.modules["boto3"] = SimpleNamespace(
    client=lambda service: None,
    resource=lambda service: None,
)
from processor import s3_writer


class FakeS3:
    def __init__(self):
        self.put = None

    def put_object(self, **kwargs):
        self.put = kwargs


def test_write_state_snapshot_uses_state_snapshot_prefix(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setattr(s3_writer, "_s3", fake_s3)
    monkeypatch.setattr(s3_writer, "BUCKET_NAME", "aegis-bucket-data")

    s3_writer.write_state_snapshot(
        "factory-b",
        "2026-05-21T10:00:03.123Z",
        {
            "pk": "FACTORY#factory-b",
            "sk": "HISTORY#STATE#2026-05-21T10:00:03.123Z",
            "factory_state": {"temperature_celsius": 31.2},
        },
    )

    assert fake_s3.put["Bucket"] == "aegis-bucket-data"
    assert fake_s3.put["Key"] == (
        "processed/factory-b/state_snapshot/"
        "yyyy=2026/mm=05/dd=21/hh=10/2026-05-21T10:00:03.123Z.json"
    )
    assert '"ttl"' not in fake_s3.put["Body"]
    assert '"sk": "HISTORY#STATE#2026-05-21T10:00:03.123Z"' in fake_s3.put["Body"]
