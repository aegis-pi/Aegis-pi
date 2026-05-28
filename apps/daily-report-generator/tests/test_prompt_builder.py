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
    assert "expected/actual count와 수집률" in prompt
    assert "collection_rate 같은 필드명을 쓰지 않는다" in prompt
    assert "핵심 지표 표와 각 섹션의 기본 표는 코드가 report-context.json 값으로 자동 삽입" in prompt
    assert "너는 Markdown 표를 만들지 않는다" in prompt
    assert "상세 분석은 각 본문 섹션에서 풀어 쓴다" in prompt
    assert "표의 행을 기계적으로 다시 읽는 식의 반복을 피한다" in prompt
    assert "주요 이벤트와 확인 필요 항목 섹션은 표가 있더라도 반드시 운영 영향 분석" in prompt
    assert "공장 상태 데이터는 28800건 중 28064건" in prompt
    assert "Risk Score 점수와 혼동하지 않는다" in prompt
    assert "JSON 필드명이나 변수명을 그대로 제목처럼 쓰지 않는다" in prompt
    assert "평균 Risk Score" in prompt
    assert "주의 상태 누적 시간" in prompt
    assert "공장 상태 데이터" in prompt
    assert "위험 점수 데이터" in prompt
    assert "AI 스코어 급등 횟수" in prompt
    assert "센서와 AI 이벤트는 없었다" in prompt
    assert "운영자 친화적인 용어" in prompt
    assert "이 수치가 뜻하는 것" in prompt
    assert "즉시 위험으로 보기는 어렵다" in prompt
    assert "보고서 신뢰도에 주는 영향" in prompt
    assert "data_quality.top_gap_windows" in prompt
    assert "최소 분 단위" in prompt
    assert "gap_minutes_by_dataset" in prompt
    assert "점수가 높을수록 안전에 가까운 지표" in prompt
    assert "현재는 회복됐지만 당시 원인은 확인 필요" in prompt
    assert "비전문 운영자도 이해할 수 있게" in prompt
    assert "정상/주의/위험 중 하나로 판단" in prompt
    assert "보고서 기준 시간대와 S3 조회 UTC 범위" in prompt
    assert "S3 partition은 UTC 기준" in prompt
    assert "events 배열의 상위 이벤트를 severity_score 순서" in prompt
    assert "snapshot final 상태" in prompt
    assert "S3 processed" in prompt
    assert "ai_spike_event_examples" in prompt
    assert "첫 1~2개를 원문 그대로 포함" in prompt
    assert "너무 짧게 쓰지 말고" in prompt
    assert "# factory-b 일일 운영 리포트 - 2026-05-27" in prompt
    assert "## 데이터 수집 상태" in prompt
    assert "## 확인 필요 항목" in prompt
