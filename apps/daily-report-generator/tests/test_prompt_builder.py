from report_generator.prompt_builder import build_prompt


def test_build_prompt_contains_operational_constraints_and_fixed_sections():
    prompt = build_prompt({
        "factory_id": "factory-b",
        "report_date": "2026-05-27",
        "risk": {"min_score": 77.16},
    })

    assert "report-context.json" in prompt
    assert "S3 raw 원본이나 JSON에 없는 사실은 절대 추가하지 않는다" in prompt
    assert "factory-b와 factory-c는 dummy/testbed 데이터" in prompt
    assert "snapshot은 마지막 전체 상태 참고용" in prompt
    assert "expected/actual count와 collection_rate 원값" in prompt
    assert "Risk Score 수치와 혼동하지 않는다" in prompt
    assert "정상/주의/위험 중 하나로 판단" in prompt
    assert "events 배열의 상위 이벤트를 severity_score 순서" in prompt
    assert "snapshot final 상태" in prompt
    assert "S3 processed" in prompt
    assert "ai_spike_event_examples" in prompt
    assert "첫 1~2개를 원문 그대로 포함" in prompt
    assert "너무 짧게 쓰지 말고" in prompt
    assert "# factory-b 일일 운영 리포트 - 2026-05-27" in prompt
    assert "## 데이터 수집 상태" in prompt
    assert "## 확인 필요 항목" in prompt
