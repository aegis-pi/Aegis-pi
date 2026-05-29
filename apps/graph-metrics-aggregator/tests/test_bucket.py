from datetime import datetime, timezone

from aggregator.bucket import bucket_end, closed_buckets, format_utc_millis, s3_metrics_5m_key


def test_closed_buckets_uses_previous_closed_window():
    now = datetime(2026, 5, 28, 10, 10, 2, tzinfo=timezone.utc)

    buckets = closed_buckets(now, 5, 1)

    assert buckets == [datetime(2026, 5, 28, 10, 5, tzinfo=timezone.utc)]
    assert format_utc_millis(bucket_end(buckets[0], 5)) == "2026-05-28T10:09:59.999Z"


def test_closed_buckets_lookback_is_oldest_first():
    now = datetime(2026, 5, 28, 10, 11, tzinfo=timezone.utc)

    buckets = closed_buckets(now, 5, 2)

    assert buckets == [
        datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 28, 10, 5, tzinfo=timezone.utc),
    ]


def test_s3_key_uses_bucket_start_partition():
    key = s3_metrics_5m_key(
        "processed_agg",
        "factory-b",
        datetime(2026, 5, 28, 10, 5, tzinfo=timezone.utc),
    )

    assert key == "processed_agg/factory-b/metrics_5m/yyyy=2026/mm=05/dd=28/hh=10/mm=05.json"

