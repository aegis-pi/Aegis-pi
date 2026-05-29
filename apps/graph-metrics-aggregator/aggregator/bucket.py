from datetime import datetime, timedelta, timezone


ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ISO_MILLIS_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    value = value.astimezone(timezone.utc).replace(microsecond=0)
    return value.strftime(ISO_FORMAT)


def format_utc_millis(value: datetime) -> str:
    value = value.astimezone(timezone.utc)
    millis = value.microsecond // 1000
    return value.strftime("%Y-%m-%dT%H:%M:%S") + f".{millis:03d}Z"


def floor_to_bucket(value: datetime, bucket_minutes: int) -> datetime:
    value = value.astimezone(timezone.utc)
    floored_minute = value.minute - (value.minute % bucket_minutes)
    return value.replace(minute=floored_minute, second=0, microsecond=0)


def bucket_end(bucket_start: datetime, bucket_minutes: int) -> datetime:
    return bucket_start + timedelta(minutes=bucket_minutes) - timedelta(milliseconds=1)


def closed_buckets(now: datetime, bucket_minutes: int, lookback_buckets: int) -> list[datetime]:
    floor = floor_to_bucket(now, bucket_minutes)
    return [
        floor - timedelta(minutes=bucket_minutes * offset)
        for offset in range(lookback_buckets, 0, -1)
    ]


def s3_metrics_5m_key(prefix: str, factory_id: str, bucket_start: datetime) -> str:
    dt = bucket_start.astimezone(timezone.utc)
    return (
        f"{prefix}/{factory_id}/metrics_5m/"
        f"yyyy={dt.year:04d}/mm={dt.month:02d}/dd={dt.day:02d}/"
        f"hh={dt.hour:02d}/mm={dt.minute:02d}.json"
    )

