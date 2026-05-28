import json
from pathlib import Path

from report_generator.aggregate_hour import aggregate_factory_hour_records


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "processed" / "factory-a"


def test_aggregate_factory_hour_preserves_stats_spikes_thresholds_and_evidence():
    summary = aggregate_factory_hour_records(
        factory_id="factory-a",
        report_date="2026-01-01",
        timezone="Asia/Seoul",
        hour="15",
        hour_window={
            "start_kst": "2026-01-01T15:00:00+09:00",
            "end_kst": "2026-01-01T15:59:59+09:00",
        },
        records_by_dataset=_load_fixture_records(),
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/factory-a",
    )

    assert summary["status"] == "success"
    assert summary["summary_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/intermediate/hourly/hh=15.json"

    assert summary["input_counts"]["factory_state"] == 3
    assert summary["input_counts"]["risk_score"] == 3
    assert summary["input_counts"]["infra_state"] == 2
    assert summary["input_counts"]["state_snapshot"] == 1
    assert summary["input_counts"]["duplicate_records"] == 1
    assert summary["expected_counts"] == {
        "factory_state": 1200,
        "risk_score": 1200,
        "infra_state": 180,
    }
    assert summary["data_quality"]["factory_state_collection_rate"] == 0.0025
    assert summary["data_quality"]["infra_state_collection_rate"] == 0.0111
    assert summary["data_quality"]["data_gap_count"] > 0
    assert summary["data_quality"]["max_gap_minutes"] > 40
    assert summary["data_quality"]["gap_windows"][0]["dataset"] in ("factory_state", "risk_score")
    assert summary["data_quality"]["gap_windows"][0]["gap_type"] == "hour_end"
    assert summary["data_quality"]["gap_windows"][0]["duration_minutes"] > 49

    assert summary["risk"]["avg_score"] == 66.73
    assert summary["risk"]["min_score"] == 51.2
    assert summary["risk"]["max_score"] == 91.0
    assert summary["risk"]["p05_score"] == 51.2
    assert summary["risk"]["p95_score"] == 91.0
    assert summary["risk"]["warning_minutes"] == 0.1
    assert summary["risk"]["danger_minutes"] == 0
    assert summary["risk"]["top_causes"] == ["temperature", "ai_event_rate"]
    assert summary["risk"]["worst_periods"][0]["evidence_message_ids"] == [
        "factory-a:factory_state:worker2:2026-01-01T06:10:06Z"
    ]

    assert summary["factory_state"]["temperature_avg"] == 37.43
    assert summary["factory_state"]["temperature_max"] == 42.8
    assert summary["factory_state"]["temperature_p05"] == 30.0
    assert summary["factory_state"]["temperature_p95"] == 42.8
    assert summary["factory_state"]["temperature_over_threshold_minutes"] == 0.1
    assert summary["factory_state"]["max_fall_score"] == 0.91
    assert summary["factory_state"]["fall_score_p95"] == 0.91
    assert summary["factory_state"]["fall_score_over_threshold_seconds"] == 6
    assert summary["factory_state"]["abnormal_sound_count"] == 1
    assert summary["factory_state"]["spike_events"][0]["type"] == "ai_score_spike"
    assert summary["factory_state"]["spike_events"][0]["evidence"]["evidence_message_ids"] == [
        "factory-a:factory_state:worker2:2026-01-01T06:10:03Z",
        "factory-a:factory_state:worker2:2026-01-01T06:10:06Z",
    ]

    assert summary["infra"]["node_not_ready_count"] == 1
    assert summary["infra"]["node_not_ready_minutes"] == 0.33
    assert summary["infra"]["workload_restart_total"] == 3
    assert summary["infra"]["unhealthy_workload_minutes"] == 0.33
    assert summary["infra"]["not_ready_nodes"] == [
        {"node_id": "worker2", "sample_count": 1}
    ]
    assert summary["infra"]["unhealthy_workloads"] == [
        {"workload": "monitoring/bme280-sensor", "sample_count": 1}
    ]
    assert summary["pipeline"]["pipeline_warning_minutes"] == 0.38
    assert summary["snapshot"] == {
        "state_snapshot_count": 1,
        "final_updated_at": "2026-01-01T06:10:07.000Z",
        "last_factory_state_at": "2026-01-01T06:10:06Z",
        "last_infra_state_at": "2026-01-01T06:10:20Z",
        "final_risk_score": 51.2,
        "final_risk_level": "warning",
        "final_pipeline_status": "warning",
        "final_nodes_ready": 2,
        "final_nodes_total": 3,
        "final_pods_ready": 5,
        "final_pods_total": 6,
    }

    event_types = [event["type"] for event in summary["events"]]
    assert "risk_degradation" in event_types
    assert "sensor_threshold_exceeded" in event_types
    assert "ai_score_spike" in event_types
    assert "node_not_ready" in event_types
    assert "workload_unhealthy" in event_types
    node_event = next(event for event in summary["events"] if event["type"] == "node_not_ready")
    assert node_event["time_range"] == "15:10~15:10"
    assert node_event["evidence"]["evidence_message_ids"] == [
        "factory-a:infra_state:cluster:2026-01-01T06:10:20Z"
    ]
    assert summary["events"] == sorted(summary["events"], key=lambda event: event["severity_score"], reverse=True)


def test_aggregate_factory_hour_includes_millisecond_records_at_hour_end():
    summary = aggregate_factory_hour_records(
        factory_id="factory-a",
        report_date="2026-01-01",
        timezone="Asia/Seoul",
        hour="15",
        hour_window={
            "start_kst": "2026-01-01T15:00:00+09:00",
            "end_kst": "2026-01-01T15:59:59+09:00",
        },
        records_by_dataset={
            "factory_state": [
                {
                    "factory_id": "factory-a",
                    "source_message_id": "factory-state-ms",
                    "source_timestamp": "2026-01-01T06:59:59.722Z",
                    "data": {"temperature_celsius": 24.0},
                }
            ],
            "risk_score": [
                {
                    "factory_id": "factory-a",
                    "source_message_id": "risk-score-ms",
                    "source_timestamp": "2026-01-01T06:59:59.722Z",
                    "risk": {"score": 100, "level": "safe"},
                    "pipeline_status": {"status": "normal"},
                }
            ],
            "infra_state": [],
            "state_snapshot": [
                {
                    "factory_id": "factory-a",
                    "updated_at": "2026-01-01T06:59:59.722Z",
                    "factory_state": {},
                    "infra_state": {},
                    "risk": {},
                    "pipeline_status": {},
                }
            ],
        },
    )

    assert summary["input_counts"]["factory_state"] == 1
    assert summary["input_counts"]["risk_score"] == 1
    assert summary["input_counts"]["state_snapshot"] == 1


def _load_fixture_records():
    return {
        dataset: [
            json.loads(path.read_text())
            for path in sorted((FIXTURE_ROOT / dataset).glob("*.json"))
        ]
        for dataset in ("factory_state", "risk_score", "infra_state", "state_snapshot")
    }
