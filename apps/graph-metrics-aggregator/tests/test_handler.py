from datetime import datetime, timezone

from aggregator import handler as handler_module


def test_handler_processes_manual_bucket(monkeypatch):
    query_calls = []
    put_items = []
    put_s3 = []

    monkeypatch.setenv("GRAPH_TTL_HOURS", "48")
    monkeypatch.setenv("EXPECTED_SAMPLE_INTERVAL_SECONDS", "3")
    monkeypatch.setenv("AI_SCORE_THRESHOLD", "0.7")
    monkeypatch.setenv("S3_OUTPUT_PREFIX", "processed_agg")
    monkeypatch.setattr(handler_module.bucket, "utc_now", lambda: datetime(2026, 5, 28, 10, 10, 3, tzinfo=timezone.utc))

    def fake_query(factory_id, bucket_start, bucket_end):
        query_calls.append((factory_id, bucket_start, bucket_end))
        return []

    monkeypatch.setattr(handler_module.dynamo, "query_history", fake_query)
    monkeypatch.setattr(handler_module.dynamo, "put_graph_item", lambda item: put_items.append(item))
    monkeypatch.setattr(handler_module.s3_writer, "put_graph_object", lambda item, prefix: put_s3.append((item, prefix)) or "s3-key")

    result = handler_module.handler(
        {
            "factories": ["factory-b"],
            "bucket_start": "2026-05-28T10:05:00Z",
            "write_dynamodb": True,
            "write_s3": True,
        },
        None,
    )

    assert result["status"] == "ok"
    assert result["processed"] == [
        {
            "factory_id": "factory-b",
            "bucket_start": "2026-05-28T10:05:00Z",
            "source_count": 0,
            "dynamodb_sk": "GRAPH#5M#2026-05-28T10:05:00Z",
            "s3_key": "s3-key",
        }
    ]
    assert query_calls[0][0] == "factory-b"
    assert put_items[0]["quality"]["is_empty"] is True
    assert put_s3[0][1] == "processed_agg"

