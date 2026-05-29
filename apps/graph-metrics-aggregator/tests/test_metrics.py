from datetime import datetime, timezone

from aggregator.bucket import bucket_end
from aggregator.metrics import aggregate_graph_item


def test_aggregate_graph_item_summarizes_sensor_risk_ai_and_infra():
    start = datetime(2026, 5, 28, 10, 5, tzinfo=timezone.utc)
    end = bucket_end(start, 5)
    created_at = datetime(2026, 5, 28, 10, 10, 3, tzinfo=timezone.utc)
    items = [
        _history_item("2026-05-28T10:05:01Z", temperature=24.0, risk=98.0, fire=0.1, fall=0.2, bend=0.3, cpu=(20, 40)),
        _history_item("2026-05-28T10:06:01Z", temperature=26.0, risk=90.0, fire=0.8, fall=0.6, bend=0.2, cpu=(60, 80)),
        _history_item("2026-05-28T10:07:01Z", temperature=25.0, risk=95.0, fire=0.4, fall=0.9, bend=0.1, cpu=(30, None)),
    ]

    graph = aggregate_graph_item(
        "factory-b",
        start,
        end,
        items,
        created_at=created_at,
        graph_ttl_hours=48,
        expected_sample_interval_seconds=3,
        ai_score_threshold=0.7,
    )

    assert graph["pk"] == "FACTORY#factory-b"
    assert graph["sk"] == "GRAPH#5M#2026-05-28T10:05:00Z"
    assert graph["ttl"] == 1780135803
    assert graph["sensor"]["temperature_celsius"]["count"] == 3
    assert graph["sensor"]["temperature_celsius"]["min"] == 24.0
    assert graph["sensor"]["temperature_celsius"]["max_at"] == "2026-05-28T10:06:01Z"
    assert graph["sensor"]["temperature_celsius"]["mean"] == 25.0
    assert graph["risk"]["score"]["min"] == 90.0
    assert graph["ai_detection"]["max_score"] == 0.9
    assert graph["ai_detection"]["max_score_type"] == "fall_score"
    assert graph["ai_detection"]["above_threshold_count"] == 2
    assert graph["ai_detection"]["by_type"]["fire_score"]["above_threshold_count"] == 1
    assert graph["ai_detection"]["by_type"]["fall_score"]["first_above_threshold_at"] == "2026-05-28T10:07:01Z"
    assert graph["infra"]["cpu_usage_percent"]["first"] == 30.0
    assert graph["infra"]["cpu_usage_percent"]["max"] == 70.0
    assert graph["infra"]["cpu_usage_percent"]["last"] == 30.0
    assert graph["quality"]["expected_count"] == 100
    assert graph["quality"]["source_count"] == 3
    assert graph["quality"]["infra_values_from_snapshot"] is True


def test_aggregate_graph_item_writes_empty_bucket():
    start = datetime(2026, 5, 28, 10, 5, tzinfo=timezone.utc)
    created_at = datetime(2026, 5, 28, 10, 10, 3, tzinfo=timezone.utc)

    graph = aggregate_graph_item(
        "factory-b",
        start,
        bucket_end(start, 5),
        [],
        created_at=created_at,
        graph_ttl_hours=48,
        expected_sample_interval_seconds=3,
        ai_score_threshold=0.7,
    )

    assert graph["sensor"] == {}
    assert graph["risk"] == {}
    assert graph["infra"] == {}
    assert graph["ai_detection"] == {
        "threshold": 0.7,
        "max_score": None,
        "max_score_type": None,
        "max_score_at": None,
        "above_threshold_count": 0,
        "by_type": {},
    }
    assert graph["quality"]["is_empty"] is True
    assert graph["quality"]["is_partial"] is True


def test_aggregate_graph_item_deduplicates_repeated_snapshot_payloads():
    start = datetime(2026, 5, 28, 10, 5, tzinfo=timezone.utc)
    end = bucket_end(start, 5)
    created_at = datetime(2026, 5, 28, 10, 10, 3, tzinfo=timezone.utc)
    first = _history_item("2026-05-28T10:05:01.000Z", temperature=24.0, risk=98.0, fire=0.1, fall=0.2, bend=0.3, cpu=(20, 40))
    duplicate = _history_item("2026-05-28T10:05:02.000Z", temperature=24.0, risk=98.0, fire=0.1, fall=0.2, bend=0.3, cpu=(20, 40))
    second = _history_item("2026-05-28T10:05:04.000Z", temperature=26.0, risk=90.0, fire=0.8, fall=0.1, bend=0.1, cpu=(60, 80))
    first["factory_state"]["source_timestamp"] = "2026-05-28T10:05:00Z"
    duplicate["factory_state"]["source_timestamp"] = "2026-05-28T10:05:00Z"
    second["factory_state"]["source_timestamp"] = "2026-05-28T10:05:03Z"
    first["risk"]["calculated_at"] = "2026-05-28T10:05:01.000Z"
    duplicate["risk"]["calculated_at"] = "2026-05-28T10:05:01.000Z"
    second["risk"]["calculated_at"] = "2026-05-28T10:05:04.000Z"
    first["infra_state"]["source_timestamp"] = "2026-05-28T10:04:49Z"
    duplicate["infra_state"]["source_timestamp"] = "2026-05-28T10:04:49Z"
    second["infra_state"]["source_timestamp"] = "2026-05-28T10:05:09Z"

    graph = aggregate_graph_item(
        "factory-b",
        start,
        end,
        [first, duplicate, second],
        created_at=created_at,
        graph_ttl_hours=48,
        expected_sample_interval_seconds=3,
        ai_score_threshold=0.7,
    )

    assert graph["quality"]["source_count"] == 3
    assert graph["sensor"]["temperature_celsius"]["count"] == 2
    assert graph["sensor"]["temperature_celsius"]["mean"] == 25.0
    assert graph["sensor"]["temperature_celsius"]["first_at"] == "2026-05-28T10:05:00Z"
    assert graph["risk"]["score"]["count"] == 2
    assert graph["ai_detection"]["by_type"]["fire_score"]["count"] == 2
    assert graph["ai_detection"]["above_threshold_count"] == 1
    assert graph["infra"]["cpu_usage_percent"]["count"] == 2


def _history_item(at, *, temperature, risk, fire, fall, bend, cpu):
    return {
        "sk": f"HISTORY#STATE#{at}",
        "updated_at": at,
        "factory_state": {
            "temperature_celsius": temperature,
            "humidity_percent": 40.0,
            "pressure_hpa": 1008.0,
            "fire_score": fire,
            "fall_score": fall,
            "bend_score": bend,
        },
        "risk": {"score": risk},
        "infra_state": {
            "nodes": [
                {"cpu_usage_percent": cpu[0], "memory_usage_percent": 50.0, "disk_usage_percent": 70.0},
                {"cpu_usage_percent": cpu[1], "memory_usage_percent": 60.0, "disk_usage_percent": 72.0},
            ]
        },
    }
