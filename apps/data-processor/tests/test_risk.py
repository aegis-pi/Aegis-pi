from processor.risk import calculate


def _sensor(temp=20.0, humid=40.0, fire=0.0, fall=0.0, bend=0.0, sound="none"):
    return {
        "temperature_celsius": temp,
        "humidity_percent": humid,
        "fire_score": fire,
        "fall_score": fall,
        "bend_score": bend,
        "abnormal_sound": sound,
        "pressure_hpa": 1013.0,
        "sample_count": 1,
    }


def test_normal_conditions():
    result = calculate(_sensor())
    assert result["level"] == "safe"
    assert result["score"] == 100.0


def test_critical_temperature():
    result = calculate(_sensor(temp=40.0))
    assert result["level"] == "warning"
    assert result["score"] == 84.0
    assert result["base_score"] == 90.0
    assert result["gates"][0]["name"] == "temperature_critical"


def test_warning_temperature():
    result = calculate(_sensor(temp=35.0))
    assert result["score"] < 100.0
    assert result["score"] > 57.14


def test_high_humidity():
    result = calculate(_sensor(humid=90.0))
    assert result["score"] == 84.0
    assert result["base_score"] == 95.0


def test_ai_fire_score():
    result = calculate(_sensor(fire=1.0))
    assert result["score"] == 49.0
    assert result["level"] == "danger"
    assert any(c["field"] == "ai_event_rate" for c in result["top_causes"])


def test_combined_high_risk():
    result = calculate(_sensor(temp=40.0, humid=90.0, fire=1.0))
    assert result["level"] == "danger"
    assert result["score"] == 49.0


def test_top_causes_sorted():
    result = calculate(_sensor(temp=40.0, fire=0.5))
    causes = result["top_causes"]
    for i in range(len(causes) - 1):
        assert causes[i]["contribution"] >= causes[i + 1]["contribution"]


def test_all_nodes_not_ready_caps_score_to_danger():
    infra = {
        "nodes_ready": 0,
        "nodes_total": 2,
        "pods_ready": 2,
        "pods_total": 2,
        "nodes": [
            {"ready": False, "disk_usage_percent": 25, "network_reachability": "ok"},
            {"ready": False, "disk_usage_percent": 26, "network_reachability": "ok"},
        ],
        "devices": {
            "bme280": {"available": True},
            "camera": {"available": True},
            "microphone": {"available": True},
        },
    }

    result = calculate(_sensor(), infra, {"status": "normal", "latest_infra_state_age_seconds": 5})

    assert result["base_score"] == 80.0
    assert result["score"] == 0.0
    assert result["level"] == "danger"
    assert result["gates"][0]["name"] == "nodes_all_not_ready"
    assert result["gates"][0]["score_cap"] == 0.0
    assert result["top_causes"][0]["source"] == "gate"


def test_pipeline_warning_caps_score_to_warning():
    result = calculate(_sensor(), {}, {"status": "warning", "latest_infra_state_age_seconds": 90})

    assert result["score"] == 84.0
    assert result["level"] == "warning"
    assert result["gates"][0]["name"] == "pipeline_status_warning"


def test_pipeline_outage_caps_score_to_zero():
    result = calculate(_sensor(), {}, {"status": "critical", "latest_infra_state_age_seconds": 301})

    assert result["score"] == 0.0
    assert result["level"] == "danger"
    assert result["gates"][0]["name"] == "pipeline_status_outage"
    assert result["gates"][0]["score_cap"] == 0.0
