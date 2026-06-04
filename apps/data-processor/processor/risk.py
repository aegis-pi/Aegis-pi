from processor.pipeline_status import CRITICAL_SECONDS as FRESHNESS_CRITICAL_SECONDS
from processor.pipeline_status import WARNING_SECONDS as FRESHNESS_WARNING_SECONDS

# Higher score is safer: 100-85 safe, 84-50 warning, 49-0 danger.
_WEIGHTS = {
    "temperature": 10.0,
    "humidity": 5.0,
    "pressure": 5.0,
    "ai_event_rate": 15.0,
    "node_status": 20.0,
    "pod_health": 15.0,
    "device_availability": 10.0,
    "data_freshness": 10.0,
    "storage_pressure": 5.0,
    "network_reachability": 5.0,
}

_TEMP_WARNING = 32.0
_TEMP_CRITICAL = 38.0
_HUMID_WARNING = 70.0
_HUMID_CRITICAL = 85.0
_PRESSURE_LOW_WARNING = 990.0
_PRESSURE_LOW_CRITICAL = 970.0
_PRESSURE_HIGH_WARNING = 1030.0
_PRESSURE_HIGH_CRITICAL = 1050.0
_STORAGE_WARNING = 75.0
_STORAGE_CRITICAL = 90.0
_FRESHNESS_OUTAGE_SECONDS = 300
_REQUIRED_DEVICES = ("bme280", "camera", "microphone")

_LEVEL_SAFE_MIN = 85.0
_LEVEL_WARNING_MIN = 50.0
_WARNING_CAP = 84.0
_DANGER_CAP = 49.0


def calculate(
    factory_state: dict,
    infra_state: dict | None = None,
    pipeline_status: dict | None = None,
) -> dict:
    contributions = []
    gates = []

    _add_weighted(
        contributions,
        "temperature",
        factory_state.get("temperature_celsius"),
        _linear_high_risk(factory_state.get("temperature_celsius"), _TEMP_WARNING, _TEMP_CRITICAL),
    )
    _add_weighted(
        contributions,
        "humidity",
        factory_state.get("humidity_percent"),
        _linear_high_risk(factory_state.get("humidity_percent"), _HUMID_WARNING, _HUMID_CRITICAL),
    )
    _add_weighted(
        contributions,
        "pressure",
        factory_state.get("pressure_hpa"),
        _pressure_risk(factory_state.get("pressure_hpa")),
    )
    _add_weighted(
        contributions,
        "ai_event_rate",
        max(
            _number(factory_state.get("fire_score")),
            _number(factory_state.get("fall_score")),
            _number(factory_state.get("bend_score")),
        ),
        _ai_risk(
            factory_state.get("fire_score"),
            factory_state.get("fall_score"),
            factory_state.get("bend_score"),
            factory_state.get("abnormal_sound", "none"),
        ),
    )
    gates.extend(_factory_state_gates(factory_state))

    if infra_state:
        _add_weighted(
            contributions,
            "node_status",
            _ready_value(infra_state, "nodes_ready", "nodes_total"),
            _availability_risk(infra_state.get("nodes_ready"), infra_state.get("nodes_total")),
        )
        _add_weighted(
            contributions,
            "pod_health",
            _ready_value(infra_state, "pods_ready", "pods_total"),
            _availability_risk(infra_state.get("pods_ready"), infra_state.get("pods_total")),
        )
        _add_weighted(
            contributions,
            "device_availability",
            _device_value(infra_state),
            _device_risk(infra_state),
        )
        _add_weighted(
            contributions,
            "storage_pressure",
            _max_node_metric(infra_state, "disk_usage_percent"),
            _linear_high_risk(_max_node_metric(infra_state, "disk_usage_percent"), _STORAGE_WARNING, _STORAGE_CRITICAL),
        )
        _add_weighted(
            contributions,
            "network_reachability",
            _network_value(infra_state),
            _network_risk(infra_state),
        )
        gates.extend(_infra_gates(infra_state, factory_state))

    _add_weighted(
        contributions,
        "data_freshness",
        (pipeline_status or {}).get("latest_infra_state_age_seconds"),
        _freshness_risk(pipeline_status),
    )
    gates.extend(_pipeline_gates(pipeline_status))

    base_score = round(max(0.0, 100.0 - sum(c["contribution"] for c in contributions)), 2)
    score = _apply_gate_caps(base_score, gates)
    base_level = _level(base_score)
    level = _level(score)

    contributions.extend(_gate_causes(gates, base_score, score))
    contributions.sort(key=lambda x: (_severity_rank(x.get("severity")), x["contribution"]), reverse=True)

    return {
        "score": score,
        "base_score": base_score,
        "level": level,
        "base_level": base_level,
        "top_causes": contributions[:5],
        "gates": gates,
    }


def _add_weighted(contributions: list[dict], field: str, value, risk_ratio: float):
    risk_ratio = max(0.0, min(float(risk_ratio), 1.0))
    if risk_ratio <= 0:
        return
    contribution = round(_WEIGHTS[field] * risk_ratio, 2)
    contributions.append({
        "field": field,
        "reason": f"{field}_weighted_penalty",
        "value": value,
        "contribution": contribution,
        "severity": _contribution_severity(contribution),
        "source": "weighted",
    })


def _linear_high_risk(value, warning: float, critical: float) -> float:
    value = _nullable_number(value)
    if value is None:
        return 0.0
    if value >= critical:
        return 1.0
    if value >= warning:
        return (value - warning) / (critical - warning)
    return 0.0


def _pressure_risk(pressure) -> float:
    pressure = _nullable_number(pressure)
    if pressure is None:
        return 0.0
    if pressure <= _PRESSURE_LOW_CRITICAL or pressure >= _PRESSURE_HIGH_CRITICAL:
        return 1.0
    if pressure < _PRESSURE_LOW_WARNING:
        return (_PRESSURE_LOW_WARNING - pressure) / (_PRESSURE_LOW_WARNING - _PRESSURE_LOW_CRITICAL)
    if pressure > _PRESSURE_HIGH_WARNING:
        return (pressure - _PRESSURE_HIGH_WARNING) / (_PRESSURE_HIGH_CRITICAL - _PRESSURE_HIGH_WARNING)
    return 0.0


def _ai_risk(fire, fall, bend, sound: str) -> float:
    peak = max(_number(fire), _number(fall), _number(bend))
    sound_bonus = 0.5 if sound not in ("none", "") else 0.0
    return min(1.0, peak + (sound_bonus / 10.0))


def _availability_risk(ready, total) -> float:
    ready = int(_number(ready))
    total = int(_number(total))
    if total <= 0:
        return 0.0
    return max(0.0, min((total - ready) / total, 1.0))


def _device_risk(infra_state: dict) -> float:
    devices = infra_state.get("devices") or {}
    if not devices:
        return 0.0
    unavailable = 0
    total = 0
    for name in _REQUIRED_DEVICES:
        if name not in devices:
            continue
        total += 1
        if devices[name].get("available") is False or devices[name].get("status") == "unavailable":
            unavailable += 1
    return unavailable / total if total else 0.0


def _freshness_risk(pipeline_status: dict | None) -> float:
    if not pipeline_status:
        return 0.0
    if pipeline_status.get("status") == "critical":
        return 1.0
    age = pipeline_status.get("latest_infra_state_age_seconds")
    age = _nullable_number(age)
    if age is None:
        return 1.0
    if age > FRESHNESS_CRITICAL_SECONDS:
        return 1.0
    if age > FRESHNESS_WARNING_SECONDS:
        return (age - FRESHNESS_WARNING_SECONDS) / (FRESHNESS_CRITICAL_SECONDS - FRESHNESS_WARNING_SECONDS)
    return 0.0


def _network_risk(infra_state: dict) -> float:
    nodes = infra_state.get("nodes") or []
    if not nodes:
        return 0.0
    bad = 0
    total = 0
    for node in nodes:
        status = str(node.get("network_reachability", "unknown")).lower()
        if status == "unknown":
            continue
        total += 1
        if status not in ("ok", "reachable", "ready"):
            bad += 1
    return bad / total if total else 0.0


def _infra_gates(infra_state: dict, factory_state: dict) -> list[dict]:
    gates = []
    nodes_ready = int(_number(infra_state.get("nodes_ready")))
    nodes_total = int(_number(infra_state.get("nodes_total")))
    pods_ready = int(_number(infra_state.get("pods_ready")))
    pods_total = int(_number(infra_state.get("pods_total")))

    if nodes_total > 0 and nodes_ready == 0:
        gates.append(_gate("nodes_all_not_ready", "danger", "node_status", f"{nodes_ready}/{nodes_total}", score_cap=0.0))
    elif nodes_total > 0 and nodes_ready < nodes_total:
        gates.append(_gate("nodes_partially_not_ready", "warning", "node_status", f"{nodes_ready}/{nodes_total}"))

    if pods_total > 0 and pods_ready == 0:
        gates.append(_gate("pods_all_unready", "danger", "pod_health", f"{pods_ready}/{pods_total}"))
    elif pods_total > 0 and pods_ready < pods_total:
        gates.append(_gate("pods_partially_unready", "warning", "pod_health", f"{pods_ready}/{pods_total}"))

    unavailable = _unavailable_devices(infra_state)
    if unavailable:
        level = "danger" if "bme280" in unavailable and int(_number(factory_state.get("sample_count"))) == 0 else "warning"
        gates.append(_gate("required_device_unavailable", level, "device_availability", ",".join(unavailable)))

    return gates


def _pipeline_gates(pipeline_status: dict | None) -> list[dict]:
    if not pipeline_status:
        return []
    status = pipeline_status.get("status")
    age = _nullable_number(pipeline_status.get("latest_infra_state_age_seconds"))
    if age is not None and age > _FRESHNESS_OUTAGE_SECONDS:
        return [
            _gate(
                "pipeline_status_outage",
                "danger",
                "data_freshness",
                f"stale_over_{_FRESHNESS_OUTAGE_SECONDS}s",
                score_cap=0.0,
            )
        ]
    if status == "critical":
        return [_gate("pipeline_status_critical", "danger", "data_freshness", status)]
    if status == "warning":
        return [_gate("pipeline_status_warning", "warning", "data_freshness", status)]
    return []


def _factory_state_gates(factory_state: dict) -> list[dict]:
    gates = []
    temp = _nullable_number(factory_state.get("temperature_celsius"))
    humid = _nullable_number(factory_state.get("humidity_percent"))
    fire = _number(factory_state.get("fire_score"))
    fall = _number(factory_state.get("fall_score"))
    bend = _number(factory_state.get("bend_score"))
    ai_peak = max(fire, fall, bend)
    sound = factory_state.get("abnormal_sound", "none")

    if temp is not None and temp >= _TEMP_CRITICAL:
        gates.append(_gate("temperature_critical", "warning", "temperature", temp))
    if humid is not None and humid >= _HUMID_CRITICAL:
        gates.append(_gate("humidity_critical", "warning", "humidity", humid))
    if ai_peak >= 0.95:
        gates.append(_gate("ai_score_critical", "danger", "ai_event_rate", round(ai_peak, 4)))
    elif ai_peak >= 0.8 or (ai_peak >= 0.6 and sound not in ("none", "")):
        gates.append(_gate("ai_score_warning", "warning", "ai_event_rate", round(ai_peak, 4)))

    return gates


def _gate(name: str, level: str, field: str, value, score_cap: float | None = None) -> dict:
    gate = {"name": name, "level": level, "field": field, "value": value}
    if score_cap is not None:
        gate["score_cap"] = score_cap
    return gate


def _apply_gate_caps(base_score: float, gates: list[dict]) -> float:
    score = base_score
    explicit_caps = [float(gate["score_cap"]) for gate in gates if "score_cap" in gate]
    if explicit_caps:
        score = min(score, min(explicit_caps))
    if any(gate["level"] == "danger" for gate in gates):
        score = min(score, _DANGER_CAP)
    elif any(gate["level"] == "warning" for gate in gates):
        score = min(score, _WARNING_CAP)
    return round(score, 2)


def _gate_causes(gates: list[dict], base_score: float, score: float) -> list[dict]:
    causes = []
    for gate in gates:
        cap_delta = max(base_score - score, 0.0)
        causes.append({
            "field": gate["field"],
            "reason": gate["name"],
            "value": gate["value"],
            "contribution": round(max(cap_delta, _WEIGHTS.get(gate["field"], 0.0)), 2),
            "severity": gate["level"],
            "source": "gate",
        })
    return causes


def _unavailable_devices(infra_state: dict) -> list[str]:
    devices = infra_state.get("devices") or {}
    unavailable = []
    for name in _REQUIRED_DEVICES:
        info = devices.get(name)
        if info and (info.get("available") is False or info.get("status") == "unavailable"):
            unavailable.append(name)
    return unavailable


def _max_node_metric(infra_state: dict, metric: str) -> float | None:
    values = [_nullable_number(node.get(metric)) for node in infra_state.get("nodes", []) if isinstance(node, dict)]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def _ready_value(infra_state: dict, ready_key: str, total_key: str) -> str:
    return f"{int(_number(infra_state.get(ready_key)))}/{int(_number(infra_state.get(total_key)))}"


def _device_value(infra_state: dict) -> str:
    unavailable = _unavailable_devices(infra_state)
    return "all_available" if not unavailable else ",".join(unavailable)


def _network_value(infra_state: dict) -> str:
    statuses = [str(node.get("network_reachability", "unknown")) for node in infra_state.get("nodes", [])]
    return ",".join(statuses) if statuses else "unknown"


def _contribution_severity(contribution: float) -> str:
    if contribution >= 20:
        return "danger"
    if contribution > 0:
        return "warning"
    return "safe"


def _severity_rank(severity: str | None) -> int:
    return {"danger": 3, "warning": 2, "safe": 1}.get(severity or "", 0)


def _nullable_number(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _number(value) -> float:
    number = _nullable_number(value)
    return number if number is not None else 0.0


def _level(score: float) -> str:
    if score >= _LEVEL_SAFE_MIN:
        return "safe"
    if score >= _LEVEL_WARNING_MIN:
        return "warning"
    return "danger"
