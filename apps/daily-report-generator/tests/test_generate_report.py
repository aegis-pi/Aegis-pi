from report_generator.bedrock_client import MockBedrockReportClient
from report_generator.generate_report import generate_factory_report


def test_generate_factory_report_uses_context_only_and_returns_markdown_keys():
    context = _report_context()
    client = MockBedrockReportClient(
        "\n".join([
            "# factory-a 2026-01-01 일일 운영 리포트",
            "",
            "- Risk 최소 점수: 51.2",
            "- Risk 최대 점수: 99.0",
            "- factory_state 수집: 1000/1200, collection_rate 0.9986",
            "- infra_state 수집: 150/180, collection_rate 0.9949",
            "- 이 초안은 운영자 검토가 필요합니다.",
        ])
    )

    result = generate_factory_report(
        report_context=context,
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/factory-a",
        bedrock_client=client,
    )

    assert result["status"] == "success"
    assert result["report_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/report.md"
    assert result["metadata_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/factory-a/generation-metadata.json"
    assert result["generation_metadata"]["model_id"] == "mock-bedrock"
    assert result["markdown"].endswith("\n")
    assert "report-context.json" in client.prompts[0]
    assert "factory-a" in client.prompts[0]
    assert "source_message_id" not in client.prompts[0]
    assert "raw_body" not in client.prompts[0]


def test_generate_factory_report_rejects_missing_context_invariants():
    result = generate_factory_report(
        report_context=_report_context(),
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/factory-a",
        bedrock_client=MockBedrockReportClient("# 잘못된 보고서\n\n다른 날짜와 수치"),
    )

    assert result["status"] == "validation_failed"
    assert "missing invariant value: factory-a" in result["validation_errors"]
    assert "missing invariant value: 2026-01-01" in result["validation_errors"]
    assert "report_key" not in result


def _report_context():
    return {
        "schema_version": "0.1.0",
        "context_type": "daily_factory_report",
        "factory_id": "factory-a",
        "report_date": "2026-01-01",
        "timezone": "Asia/Seoul",
        "factory_profile": {
            "environment_type": "physical-rpi",
            "input_module_type": "sensor",
            "interpretation_mode": "production_edge",
        },
        "data_quality": {
            "factory_state_collection_rate": 0.9986,
            "factory_state_actual_count": 1000,
            "factory_state_expected_count": 1200,
            "infra_state_collection_rate": 0.9949,
            "infra_state_actual_count": 150,
            "infra_state_expected_count": 180,
        },
        "risk": {
            "avg_score": 87.1,
            "min_score": 51.2,
            "max_score": 99.0,
            "warning_minutes": 35,
            "danger_minutes": 0,
        },
        "factory_state": {
            "temperature_max": 42.8,
            "max_fall_score": 0.91,
        },
        "infra": {
            "node_not_ready_count": 1,
            "workload_restart_total": 4,
        },
        "pipeline": {
            "pipeline_warning_minutes": 9,
            "pipeline_critical_minutes": 0,
        },
        "events": [],
        "recommended_checks": [],
        "data_limitations": [
            "Report is based on S3 processed data, not S3 raw payloads.",
            "LLM output is an operational draft and requires operator review.",
        ],
    }
