from datetime import datetime
from zoneinfo import ZoneInfo

from report_generator.time_window import prepare_report_window


def test_prepare_report_window_builds_kst_day_with_utc_partition_range():
    result = prepare_report_window(
        report_date="2026-01-01",
        timezone_name="Asia/Seoul",
        factories=["factory-a", "factory-b"],
        datasets=["factory_state", "risk_score", "infra_state"],
        output_prefix_root="reports/daily",
        now=datetime(2026, 1, 2, 0, 30, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert result["report_date"] == "2026-01-01"
    assert result["window"]["start_kst"] == "2026-01-01T00:00:00+09:00"
    assert result["window"]["end_kst"] == "2026-01-01T23:59:59+09:00"
    assert result["window"]["start_utc"] == "2025-12-31T15:00:00Z"
    assert result["window"]["end_utc"] == "2026-01-01T14:59:59Z"
    assert result["output_prefix"] == "reports/daily/yyyy=2026/mm=01/dd=01"
    assert result["hour_items"][0]["hour_window"]["start_utc"] == "2025-12-31T15:00:00Z"
    assert result["hour_items"][23]["hour_window"]["end_utc"] == "2026-01-01T14:59:59Z"
    assert result["factory_items"][1]["factory_id"] == "factory-b"
    assert result["factory_items"][1]["output_prefix"] == "reports/daily/yyyy=2026/mm=01/dd=01/factory-b"


def test_prepare_report_window_defaults_to_previous_local_day_without_report_date():
    result = prepare_report_window(
        report_date=None,
        timezone_name="Asia/Seoul",
        factories=["factory-a"],
        datasets=["factory_state"],
        output_prefix_root="reports/daily",
        now=datetime(2026, 5, 27, 0, 30, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert result["report_date"] == "2026-05-26"
