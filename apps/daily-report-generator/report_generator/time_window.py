from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_window_bound(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_hhmm_range(start: datetime, end: datetime, timezone_name: str) -> str:
    tz = ZoneInfo(timezone_name)
    return f"{start.astimezone(tz):%H:%M}~{end.astimezone(tz):%H:%M}"


def prepare_report_window(
    report_date: str | None,
    timezone_name: str,
    factories: list[str],
    datasets: list[str],
    output_prefix_root: str,
    now: datetime | None = None,
) -> dict:
    tz = ZoneInfo(timezone_name)
    target_date = _target_report_date(report_date, tz, now)
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1) - timedelta(seconds=1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    hour_items = []
    for hour in range(24):
        hour_start = start_local + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1) - timedelta(seconds=1)
        hour_items.append({
            "hour": f"{hour:02d}",
            "hour_window": {
                "start_kst": _iso_offset(hour_start),
                "end_kst": _iso_offset(hour_end),
                "start_utc": _iso_z(hour_start.astimezone(timezone.utc)),
                "end_utc": _iso_z(hour_end.astimezone(timezone.utc)),
            },
        })

    report_date_value = target_date.isoformat()
    output_prefix = (
        f"{output_prefix_root}/yyyy={target_date.year:04d}/"
        f"mm={target_date.month:02d}/dd={target_date.day:02d}"
    )
    window = {
        "start_kst": _iso_offset(start_local),
        "end_kst": _iso_offset(end_local),
        "start_utc": _iso_z(start_utc),
        "end_utc": _iso_z(end_utc),
    }
    factory_items = [
        {
            "target_type": "factory",
            "target_id": factory_id,
            "factory_id": factory_id,
            "report_date": report_date_value,
            "timezone": timezone_name,
            "window": window,
            "hour_items": hour_items,
            "datasets": datasets,
            "output_prefix": f"{output_prefix}/{factory_id}",
        }
        for factory_id in factories
    ]
    cloud_infra_item = {
        "target_type": "cloud_infra",
        "target_id": "cloud-infra",
        "report_date": report_date_value,
        "timezone": timezone_name,
        "window": window,
        "hour_items": hour_items,
        "output_prefix": f"{output_prefix}/cloud-infra",
    }
    return {
        "report_date": report_date_value,
        "timezone": timezone_name,
        "window": window,
        "hour_items": hour_items,
        "datasets": datasets,
        "output_prefix": output_prefix,
        "factory_items": factory_items,
        "report_targets": [*factory_items, cloud_infra_item],
    }


def _target_report_date(report_date: str | None, tz: ZoneInfo, now: datetime | None) -> date:
    if report_date:
        return date.fromisoformat(report_date)
    current = now or datetime.now(tz)
    return current.astimezone(tz).date() - timedelta(days=1)


def _iso_offset(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _iso_z(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
