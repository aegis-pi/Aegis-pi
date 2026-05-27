from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AggregateThresholds:
    factory_state_interval_seconds: int = 3
    risk_score_interval_seconds: int = 3
    infra_state_interval_seconds: int = 20
    risk_warning_score_max: float = 84.99
    risk_danger_score_max: float = 49.99
    temperature_warning_c: float = 32.0
    temperature_critical_c: float = 38.0
    humidity_warning_percent: float = 70.0
    humidity_critical_percent: float = 85.0
    ai_score_spike_threshold: float = 0.7
    event_merge_gap_seconds: int = 120
    max_hourly_events: int = 5


def aggregate_thresholds_from_env() -> AggregateThresholds:
    return AggregateThresholds(
        factory_state_interval_seconds=_int_env("FACTORY_STATE_INTERVAL_SECONDS", 3),
        risk_score_interval_seconds=_int_env("RISK_SCORE_INTERVAL_SECONDS", 3),
        infra_state_interval_seconds=_int_env("INFRA_STATE_INTERVAL_SECONDS", 20),
        risk_warning_score_max=_float_env("RISK_WARNING_SCORE_MAX", 84.99),
        risk_danger_score_max=_float_env("RISK_DANGER_SCORE_MAX", 49.99),
        temperature_warning_c=_float_env("TEMPERATURE_WARNING_C", 32.0),
        temperature_critical_c=_float_env("TEMPERATURE_CRITICAL_C", 38.0),
        humidity_warning_percent=_float_env("HUMIDITY_WARNING_PERCENT", 70.0),
        humidity_critical_percent=_float_env("HUMIDITY_CRITICAL_PERCENT", 85.0),
        ai_score_spike_threshold=_float_env("AI_SCORE_SPIKE_THRESHOLD", 0.7),
        event_merge_gap_seconds=_int_env("EVENT_MERGE_GAP_SECONDS", 120),
        max_hourly_events=_int_env("MAX_HOURLY_EVENTS", 5),
    )


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float_env(name: str, default: float) -> float:
    return float(os.environ.get(name, default))

