from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from report_generator.time_window import format_hhmm_range


def threshold_windows(
    samples: list[dict],
    predicate: Callable[[dict], bool],
    interval_seconds: int,
    timezone_name: str,
    event_type: str,
    severity: str,
    summary: str,
    magnitude: Callable[[list[dict]], float] | None = None,
) -> list[dict]:
    windows = []
    current = []
    for sample in sorted(samples, key=lambda item: item["timestamp"]):
        if predicate(sample):
            current.append(sample)
            continue
        if current:
            windows.append(_event_from_samples(current, interval_seconds, timezone_name, event_type, severity, summary, magnitude))
            current = []
    if current:
        windows.append(_event_from_samples(current, interval_seconds, timezone_name, event_type, severity, summary, magnitude))
    return windows


def _event_from_samples(
    samples: list[dict],
    interval_seconds: int,
    timezone_name: str,
    event_type: str,
    severity: str,
    summary: str,
    magnitude: Callable[[list[dict]], float] | None,
) -> dict:
    start = samples[0]["timestamp"]
    end = samples[-1]["timestamp"]
    duration_seconds = len(samples) * interval_seconds
    event = {
        "time_range": format_hhmm_range(start, end, timezone_name),
        "severity": severity,
        "type": event_type,
        "summary": summary,
        "duration_seconds": duration_seconds,
        "evidence": {
            "evidence_message_ids": [sample["message_id"] for sample in samples[:5]],
        },
    }
    if magnitude:
        event["magnitude"] = magnitude(samples)
    return event
