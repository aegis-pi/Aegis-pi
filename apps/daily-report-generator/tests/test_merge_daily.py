from report_generator.merge_daily import merge_factory_daily


def test_merge_factory_daily_merges_boundary_events_scores_top_n_and_context():
    hourly_summaries = [
        _hourly_summary(
            "14",
            event={
                "time_range": "14:58~14:59",
                "severity": "warning",
                "type": "sensor_threshold_exceeded",
                "summary": "Temperature exceeded warning threshold",
                "duration_seconds": 120,
                "magnitude": 8,
                "evidence": {"evidence_message_ids": ["msg-1458"]},
            },
            risk_min=70.0,
            temp_max=40.0,
            restarts=0,
        ),
        _hourly_summary(
            "15",
            event={
                "time_range": "15:00~15:07",
                "severity": "warning",
                "type": "sensor_threshold_exceeded",
                "summary": "Temperature exceeded warning threshold",
                "duration_seconds": 480,
                "magnitude": 10.8,
                "evidence": {"evidence_message_ids": ["msg-1500"]},
            },
            risk_min=51.2,
            temp_max=42.8,
            restarts=3,
        ),
        _hourly_summary(
            "16",
            event={
                "time_range": "16:30~16:31",
                "severity": "warning",
                "type": "risk_degradation",
                "summary": "Risk Score dropped below warning threshold",
                "duration_seconds": 120,
                "magnitude": 24.4,
                "evidence": {"evidence_message_ids": ["msg-1630"]},
            },
            risk_min=58.0,
            temp_max=35.0,
            restarts=0,
        ),
    ]

    result = merge_factory_daily(
        factory_id="factory-a",
        report_date="2026-01-01",
        timezone="Asia/Seoul",
        hourly_summaries=hourly_summaries,
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/factory-a",
        max_context_events=2,
    )

    assert result["daily_summary_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/factory-daily-summary.json"
    assert result["context_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report-context.json"

    daily = result["daily_summary"]
    assert daily["factory_profile"] == {
        "environment_type": "physical-rpi",
        "input_module_type": "sensor",
        "interpretation_mode": "production_edge",
    }
    assert daily["report_window"] == {
        "timezone": "Asia/Seoul",
        "start_local": "2026-01-01T14:00:00+09:00",
        "end_local": "2026-01-01T16:59:59+09:00",
        "start_utc": "2026-01-01T05:00:00Z",
        "end_utc": "2026-01-01T07:59:59Z",
        "s3_partition_timezone": "UTC",
    }
    assert daily["data_quality"]["factory_state_expected_count"] == 3600
    assert daily["data_quality"]["factory_state_actual_count"] == 3000
    assert daily["data_quality"]["factory_state_collection_rate"] == 0.8333
    assert daily["data_quality"]["missing_hour_count"] == 21
    assert daily["data_quality"]["duplicate_message_count"] == 1
    assert daily["data_quality"]["gap_minutes"] == 9
    assert daily["data_quality"]["gap_minutes_by_dataset"] == [
        {"dataset": "factory_state", "duration_minutes": 5.0},
        {"dataset": "risk_score", "duration_minutes": 4.0},
    ]
    assert daily["data_quality"]["top_gap_windows"][0]["time_range"] == "15:00~15:05"

    assert daily["risk"]["min_score"] == 51.2
    assert daily["risk"]["worst_level"] == "warning"
    assert daily["risk"]["warning_minutes"] == 12
    assert daily["risk"]["top_causes"] == ["temperature", "ai_event_rate"]
    assert daily["factory_state"]["temperature_max"] == 42.8
    assert daily["factory_state"]["temperature_over_threshold_minutes"] == 12
    assert daily["factory_state"]["ai_spike_event_count"] == 0
    assert daily["factory_state"]["ai_spike_event_examples"] == []
    assert daily["infra"]["workload_restart_total"] == 3
    assert daily["infra"]["not_ready_nodes"] == [
        {"node_id": "worker2", "sample_count": 3}
    ]
    assert daily["infra"]["likely_infra_causes"][0] == {
        "type": "node_not_ready",
        "target": "worker2",
        "sample_count": 3,
        "interpretation": "Node ready=false was observed in infra_state samples.",
    }
    assert daily["snapshot"]["state_snapshot_count"] == 3
    assert daily["snapshot"]["final_updated_at"] == "2026-01-01T16:59:59Z"
    assert daily["snapshot"]["final_pipeline_status"] == "normal"

    merged_temperature_events = [
        event for event in daily["events"]
        if event["type"] == "sensor_threshold_exceeded"
    ]
    assert len(merged_temperature_events) == 1
    assert merged_temperature_events[0]["time_range"] == "14:58~15:07"
    assert merged_temperature_events[0]["evidence"]["evidence_message_ids"] == ["msg-1458", "msg-1500"]
    assert daily["events"] == sorted(daily["events"], key=lambda event: event["severity_score"], reverse=True)
    assert len(daily["events"]) == 2

    context = result["report_context"]
    assert context["context_type"] == "daily_factory_report"
    assert context["factory_id"] == "factory-a"
    assert context["report_window"]["s3_partition_timezone"] == "UTC"
    assert len(context["events"]) == 2
    assert context["events"][0]["severity_score"] >= context["events"][1]["severity_score"]
    assert "Report is based on S3 processed data, not S3 raw payloads." in context["data_limitations"]
    assert context["recommended_checks"][0]["item"] == "Risk degradation window sensor and AI causes"
    assert "reason" in context["recommended_checks"][0]


def test_merge_factory_daily_marks_factory_b_as_testbed_dummy_context():
    result = merge_factory_daily(
        factory_id="factory-b",
        report_date="2026-01-01",
        timezone="Asia/Seoul",
        hourly_summaries=[_hourly_summary("00")],
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/factory-b",
    )

    assert result["report_context"]["factory_profile"] == {
        "environment_type": "vm-mac",
        "input_module_type": "dummy",
        "interpretation_mode": "testbed_dummy",
    }
    assert any("dummy data" in item for item in result["report_context"]["data_limitations"])


def test_merge_factory_daily_builds_full_24_hour_context_with_evidence_and_checks():
    hourly_summaries = [_hourly_summary(f"{hour:02d}") for hour in range(24)]
    for summary in hourly_summaries:
        summary["infra"]["not_ready_nodes"] = []
        summary["infra"]["unhealthy_workloads"] = []
    hourly_summaries[3]["events"] = [
        {
            "time_range": "03:10~03:11",
            "severity": "warning",
            "type": "risk_degradation",
            "summary": "Risk Score dropped below warning threshold",
            "duration_seconds": 120,
            "magnitude": 12,
            "evidence": {"evidence_message_ids": ["risk-msg-0310"]},
        },
        {
            "time_range": "03:20~03:25",
            "severity": "warning",
            "type": "node_not_ready",
            "summary": "Node not ready state detected",
            "duration_seconds": 360,
            "magnitude": 2,
            "evidence": {"evidence_message_ids": ["infra-msg-0320", "infra-msg-0321"]},
        },
    ]
    hourly_summaries[3]["risk"]["min_score"] = 77.16
    hourly_summaries[3]["risk"]["warning_minutes"] = 2
    hourly_summaries[3]["risk"]["top_causes"] = ["ai_event_rate"]
    hourly_summaries[3]["factory_state"]["spike_events"] = [
        {
            "type": "ai_score_spike",
            "summary": "fire_score exceeded spike threshold",
            "time_range": "03:31~03:31",
            "duration_seconds": 3,
            "evidence": {"evidence_message_ids": ["ai-msg-0331"]},
        },
        {
            "type": "ai_score_spike",
            "summary": "bend_score exceeded spike threshold",
            "time_range": "03:48~03:48",
            "duration_seconds": 3,
            "evidence": {"evidence_message_ids": ["ai-msg-0348"]},
        },
    ]
    hourly_summaries[3]["factory_state"]["abnormal_sound_count"] = 4
    hourly_summaries[3]["infra"]["node_not_ready_count"] = 2
    hourly_summaries[3]["infra"]["node_not_ready_minutes"] = 6
    hourly_summaries[3]["infra"]["not_ready_nodes"] = [
        {"node_id": "control-plane:Unknown", "sample_count": 18},
        {"node_id": "worker:Unknown", "sample_count": 18},
    ]
    hourly_summaries[3]["infra"]["unhealthy_workloads"] = [
        {"workload": "ai-apps/edge-iot-publisher", "sample_count": 18},
    ]

    result = merge_factory_daily(
        factory_id="factory-b",
        report_date="2026-01-01",
        timezone="Asia/Seoul",
        hourly_summaries=hourly_summaries,
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/factory-b",
    )

    context = result["report_context"]
    assert context["data_quality"]["missing_hour_count"] == 0
    assert context["data_quality"]["factory_state_expected_count"] == 28800
    assert context["data_quality"]["factory_state_actual_count"] == 24000
    assert context["factory_state"]["ai_spike_event_count"] == 2
    assert context["factory_state"]["ai_spike_event_examples"][0]["evidence_message_ids"] == ["ai-msg-0331"]
    assert context["infra"]["likely_infra_causes"][0] == {
        "type": "node_not_ready",
        "target": "control-plane:Unknown",
        "sample_count": 18,
        "interpretation": "Node ready=false was observed in infra_state samples.",
    }
    assert context["infra"]["likely_infra_causes"][2] == {
        "type": "workload_unhealthy",
        "target": "ai-apps/edge-iot-publisher",
        "sample_count": 18,
        "interpretation": "Workload ready/status indicated unhealthy state in infra_state samples.",
    }
    checks_by_item = {check["item"]: check for check in context["recommended_checks"]}
    assert checks_by_item["Risk degradation window sensor and AI causes"]["evidence_message_ids"] == ["risk-msg-0310"]
    assert checks_by_item["AI score spike source review"]["evidence_message_ids"] == ["ai-msg-0331", "ai-msg-0348"]
    assert checks_by_item["Node readiness window evidence review"]["target_nodes"][:2] == [
        "control-plane:Unknown",
        "worker:Unknown",
    ]
    assert checks_by_item["Node readiness window evidence review"]["evidence_message_ids"] == [
        "infra-msg-0320",
        "infra-msg-0321",
    ]


def _hourly_summary(hour, event=None, risk_min=91.0, temp_max=30.0, restarts=0):
    event = event or {
        "time_range": f"{hour}:00~{hour}:00",
        "severity": "info",
        "type": "pipeline_warning",
        "summary": "Pipeline status was normal",
        "duration_seconds": 60,
        "magnitude": 0,
        "evidence": {"evidence_message_ids": []},
    }
    return {
        "schema_version": "0.1.0",
        "summary_type": "factory_hour",
        "factory_id": "factory-a",
        "report_date": "2026-01-01",
        "timezone": "Asia/Seoul",
        "hour_window": {
            "start_kst": f"2026-01-01T{hour}:00:00+09:00",
            "end_kst": f"2026-01-01T{hour}:59:59+09:00",
            "start_utc": f"2026-01-01T{(int(hour) - 9) % 24:02d}:00:00Z",
            "end_utc": f"2026-01-01T{(int(hour) - 9) % 24:02d}:59:59Z",
        },
        "hour": hour,
        "status": "success",
        "input_counts": {
            "factory_state": 1000,
            "risk_score": 1000,
            "infra_state": 150,
            "invalid_records": 0,
            "duplicate_records": 1 if hour == "15" else 0,
        },
        "expected_counts": {
            "factory_state": 1200,
            "risk_score": 1200,
            "infra_state": 180,
        },
        "data_quality": {
            "factory_state_collection_rate": 0.8333,
            "risk_score_collection_rate": 0.8333,
            "infra_state_collection_rate": 0.8333,
            "data_gap_count": 2 if hour == "15" else 0,
            "max_gap_seconds": 300 if hour == "15" else 18,
            "max_gap_minutes": 5.0 if hour == "15" else 0.3,
            "gap_minutes": 10.0 if hour == "15" else 0,
            "gap_windows": [
                {
                    "dataset": "factory_state",
                    "gap_type": "hour_start",
                    "start_utc": "2026-01-01T06:00:00Z",
                    "end_utc": "2026-01-01T06:05:00Z",
                    "time_range": "15:00~15:05",
                    "duration_seconds": 300,
                    "duration_minutes": 5.0,
                },
                {
                    "dataset": "risk_score",
                    "gap_type": "hour_start",
                    "start_utc": "2026-01-01T06:00:00Z",
                    "end_utc": "2026-01-01T06:04:00Z",
                    "time_range": "15:00~15:04",
                    "duration_seconds": 240,
                    "duration_minutes": 4.0,
                },
            ] if hour == "15" else [],
        },
        "risk": {
            "avg_score": 87.0,
            "min_score": risk_min,
            "max_score": 99.0,
            "p05_score": risk_min,
            "p95_score": 98.0,
            "warning_minutes": 4 if risk_min < 85 else 0,
            "danger_minutes": 0,
            "top_causes": ["temperature", "ai_event_rate"] if risk_min < 85 else [],
            "worst_periods": [
                {
                    "time_range": f"{hour}:10~{hour}:12",
                    "min_score": risk_min,
                    "level": "warning" if risk_min < 85 else "normal",
                    "top_causes": ["temperature"],
                    "evidence_message_ids": [f"msg-{hour}10"],
                }
            ],
        },
        "factory_state": {
            "temperature_avg": 30.0,
            "temperature_max": temp_max,
            "temperature_p95": temp_max,
            "temperature_over_threshold_minutes": 4 if temp_max >= 32 else 0,
            "humidity_avg": 62.0,
            "humidity_max": 72.0,
            "max_fire_score": 0.1,
            "max_fall_score": 0.91 if risk_min < 60 else 0.2,
            "fall_score_p95": 0.91 if risk_min < 60 else 0.2,
            "fall_score_over_threshold_seconds": 120 if risk_min < 60 else 0,
            "max_bend_score": 0.33,
            "abnormal_sound_count": 0,
        },
        "infra": {
            "infra_state_count": 150,
            "node_not_ready_count": 0,
            "node_not_ready_minutes": 0,
            "workload_restart_total": restarts,
            "unhealthy_workload_minutes": 0,
            "not_ready_nodes": [{"node_id": "worker2", "sample_count": 1}],
            "unhealthy_workloads": [],
            "restart_delta": restarts,
        },
        "pipeline": {
            "pipeline_warning_minutes": 0,
            "pipeline_critical_minutes": 0,
            "max_gap_seconds": 18,
        },
        "snapshot": {
            "state_snapshot_count": 1,
            "final_updated_at": f"2026-01-01T{hour}:59:59Z",
            "last_factory_state_at": f"2026-01-01T{hour}:59:58Z",
            "last_infra_state_at": f"2026-01-01T{hour}:59:40Z",
            "final_risk_score": risk_min,
            "final_risk_level": "warning" if risk_min < 85 else "safe",
            "final_pipeline_status": "normal",
            "final_nodes_ready": 3,
            "final_nodes_total": 3,
            "final_pods_ready": 6,
            "final_pods_total": 6,
        },
        "events": [event],
    }
