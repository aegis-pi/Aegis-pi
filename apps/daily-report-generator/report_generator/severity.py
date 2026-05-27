SEVERITY_BASE_SCORE = {
    "info": 10,
    "warning": 50,
    "danger": 80,
}


def score_event(event: dict) -> dict:
    severity = event.get("severity", "info")
    base = SEVERITY_BASE_SCORE.get(severity, 10)
    duration_bonus = min(int(event.get("duration_seconds", 0)) / 60.0, 20.0)
    magnitude_bonus = float(event.get("magnitude", 0.0))
    scored = dict(event)
    scored["severity_score"] = round(base + duration_bonus + magnitude_bonus, 2)
    return scored


def top_events(events: list[dict], limit: int) -> list[dict]:
    return sorted(
        (score_event(event) for event in events),
        key=lambda event: (event["severity_score"], event.get("time_range", "")),
        reverse=True,
    )[:limit]

