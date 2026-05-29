from report_generator.bedrock_client import MockBedrockReportClient
from report_generator.generate_report import generate_factory_report


def test_generate_factory_report_uses_context_only_and_returns_markdown_keys():
    context = _report_context()
    client = MockBedrockReportClient(
        "\n".join([
            "# factory-a 2026-01-01 일일 운영 리포트",
            "",
            "## 요약",
            "",
            "- Risk 최소 점수: 51.2",
            "- Risk 최대 점수: 99.0",
            "",
            "## 데이터 수집 상태",
            "",
            "- factory_state 수집: 1000/1200, collection_rate 0.9986",
            "- infra_state 수집: 150/180, collection_rate 0.9949",
            "",
            "## Risk Score",
            "",
            "- 주의 상태 누적 시간은 원인 확인이 필요합니다.",
            "",
            "## 센서 및 AI 이벤트",
            "",
            "- 최고 온도와 낙상 스코어는 testbed 특성을 감안해 봅니다.",
            "",
            "## 인프라 상태",
            "",
            "- 워크로드 재시작 원인을 확인합니다.",
            "",
            "## 주요 이벤트",
            "",
            "- 주요 이벤트는 없습니다.",
            "",
            "## 확인 필요 항목",
            "",
            "- 권장 확인 항목은 없습니다.",
            "- Risk degradation window sensor and AI causes (우선순위 높음)",
            "",
            "## 데이터 한계",
            "",
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
    assert "## 핵심 지표 표" in result["markdown"]
    assert result["markdown"].index("## 핵심 지표 표") < result["markdown"].index("## 검증 기준 수치")
    assert "| 평균 Risk Score | 87.1 | 높을수록 안전에 가까움 |" in result["markdown"]
    assert "| 최저 Risk Score | 51.2 | 위험 기준 접근 |" in result["markdown"]
    assert "| 공장 상태 데이터 수집률 | 1000/1200, 99.86% | 양호 |" in result["markdown"]
    assert "| 인프라 상태 데이터 수집률 | 150/180, 99.49% | 양호 |" in result["markdown"]
    assert "| 워크로드 재시작 | 4회 | 재시작 원인 확인 |" in result["markdown"]
    assert result["markdown"].index("## 데이터 수집 상태") < result["markdown"].index("| 데이터 | 수집량/구간 | 수집률/시간 | 판단 |")
    assert "| 공장 상태 데이터 | 1000/1200 | 99.86% | 양호 |" in result["markdown"]
    assert "| 평균 Risk Score | 87.1 | 높을수록 안전에 가까움 |" in result["markdown"]
    assert "| 주의 상태 누적 시간 | 35분 | 원인 확인 필요 |" in result["markdown"]
    assert "| 최고 온도 | 42.8 | 임계값과 현장 조건 확인 |" in result["markdown"]
    assert "| 낙상 스코어 최고 | 0.91 | testbed/dummy 여부 구분 |" in result["markdown"]
    assert "| 노드 준비 안됨 | 1회 | 원인 확인 필요 |" in result["markdown"]
    assert "| - | 주요 이벤트 없음 | - | - | - |" in result["markdown"]
    assert "| - | 권장 확인 항목 없음 | - | - |" in result["markdown"]
    assert "- 주요 이벤트는 없습니다." in result["markdown"]
    assert "Risk 저하 구간 원인 분석" in result["markdown"]
    assert "Risk degradation window sensor and AI causes" not in result["markdown"]
    assert "## 검증 기준 수치" in result["markdown"]
    assert "보고서 window 원문: timezone=Asia/Seoul" in result["markdown"]
    assert "Risk Score 원문: avg_score=87.1, min_score=51.2, max_score=99.0" in result["markdown"]
    assert "factory_state 수집 원문: 1000/1200, collection_rate 0.9986" in result["markdown"]
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


def test_generate_factory_report_inserts_tables_after_headings_with_trailing_space():
    context = _report_context()
    client = MockBedrockReportClient(
        "\n".join([
            "# factory-a 일일 운영 리포트 - 2026-01-01",
            "",
            "## 요약",
            "",
            "factory-a 2026-01-01 요약입니다.",
            "",
            "## 인프라 상태 ",
            "",
            "현재는 회복됐지만 당시 원인은 확인 필요합니다.",
            "",
            "## 데이터 한계",
            "",
            "S3 processed 기반이며 raw 원본은 사용하지 않았습니다.",
        ])
    )

    result = generate_factory_report(
        report_context=context,
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/factory-a",
        bedrock_client=client,
    )

    assert result["status"] == "success"
    assert "## 인프라 상태 \n" not in result["markdown"]
    assert "## 인프라 상태\n\n| 항목 | 값 | 판단 |" in result["markdown"]
    assert "| 노드 준비 안됨 | 1회 | 원인 확인 필요 |" in result["markdown"]


def _report_context():
    return {
        "schema_version": "0.1.0",
        "context_type": "daily_factory_report",
        "factory_id": "factory-a",
        "report_date": "2026-01-01",
        "timezone": "Asia/Seoul",
        "report_window": {
            "timezone": "Asia/Seoul",
            "start_local": "2026-01-01T00:00:00+09:00",
            "end_local": "2026-01-01T23:59:59+09:00",
            "start_utc": "2025-12-31T15:00:00Z",
            "end_utc": "2026-01-01T14:59:59Z",
            "s3_partition_timezone": "UTC",
        },
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
