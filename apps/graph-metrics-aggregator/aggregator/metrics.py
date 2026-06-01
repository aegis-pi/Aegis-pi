import math
from datetime import timedelta

from aggregator.bucket import format_utc, format_utc_millis, parse_utc


SCHEMA_VERSION = "graph-5m-v0.1.0"
SENSOR_METRICS = {
    "temperature_celsius": "celsius",
    "humidity_percent": "percent",
    "pressure_hpa": "hPa",
}
RISK_METRICS = {"score": "score"}
INFRA_METRICS = {
    "cpu_usage_percent": "percent",
    "memory_usage_percent": "percent",
    "disk_usage_percent": "percent",
}
AI_METRICS = ("fire_score", "fall_score", "bend_score")


class NumericReducer:
    def __init__(self):
        self.values = []

    def add(self, value, at: str):
        number = _number(value)
        if number is None:
            return
        self.values.append((at, number))

    def summary(self, unit: str) -> dict | None:
        if not self.values:
            return None
        ordered = sorted(self.values, key=lambda item: item[0])
        min_at, min_value = min(ordered, key=lambda item: item[1])
        max_at, max_value = max(ordered, key=lambda item: item[1])
        first_at, first_value = ordered[0]
        last_at, last_value = ordered[-1]
        return {
            "unit": unit,
            "count": len(ordered),
            "min": _round(min_value),
            "min_at": min_at,
            "max": _round(max_value),
            "max_at": max_at,
            "mean": _round(sum(value for _, value in ordered) / len(ordered)),
            "first": _round(first_value),
            "first_at": first_at,
            "last": _round(last_value),
            "last_at": last_at,
        }


class AiReducer:
    def __init__(self, threshold: float):
        self.threshold = threshold
        self.reducers = {name: NumericReducer() for name in AI_METRICS}
        self.values = {name: [] for name in AI_METRICS}

    def add(self, metric: str, value, at: str):
        number = _number(value)
        if number is None:
            return
        self.reducers[metric].add(number, at)
        self.values[metric].append((at, number))

    def summary(self) -> dict:
        by_type = {}
        max_score = None
        max_score_type = None
        max_score_at = None
        total_above = 0

        for metric in AI_METRICS:
            values = sorted(self.values[metric], key=lambda item: item[0])
            if not values:
                continue
            base = self.reducers[metric].summary(unit="")
            above = [(at, value) for at, value in values if value >= self.threshold]
            total_above += len(above)
            by_type[metric] = {
                "count": base["count"],
                "min": base["min"],
                "max": base["max"],
                "max_at": base["max_at"],
                "mean": base["mean"],
                "last": base["last"],
                "last_at": base["last_at"],
                "threshold": self.threshold,
                "above_threshold_count": len(above),
                "above_threshold_ratio": _round(len(above) / len(values)),
                "first_above_threshold_at": above[0][0] if above else None,
            }
            metric_max = base["max"]
            if max_score is None or metric_max > max_score:
                max_score = metric_max
                max_score_type = metric
                max_score_at = base["max_at"]

        return {
            "threshold": self.threshold,
            "max_score": max_score,
            "max_score_type": max_score_type,
            "max_score_at": max_score_at,
            "above_threshold_count": total_above,
            "by_type": by_type,
        }


def aggregate_graph_item(
    factory_id: str,
    bucket_start,
    bucket_end,
    source_items: list[dict],
    *,
    created_at,
    graph_ttl_hours: int,
    expected_sample_interval_seconds: int,
    ai_score_threshold: float,
) -> dict:
    source_items = sorted(source_items, key=_item_timestamp)
    source_count = _actual_observation_count(source_items, bucket_start, bucket_end)
    expected_count = _expected_count(bucket_start, bucket_end, expected_sample_interval_seconds)
    created_at_iso = format_utc(created_at)
    bucket_start_iso = format_utc(bucket_start)
    bucket_end_iso = format_utc_millis(bucket_end)

    item = {
        "pk": f"FACTORY#{factory_id}",
        "sk": f"GRAPH#5M#{bucket_start_iso}",
        "item_type": "GRAPH#5M",
        "factory_id": factory_id,
        "schema_version": SCHEMA_VERSION,
        "bucket_minutes": int((bucket_end + timedelta(milliseconds=1) - bucket_start).total_seconds() // 60),
        "bucket_start": bucket_start_iso,
        "bucket_end": bucket_end_iso,
        "ttl": int((created_at + timedelta(hours=graph_ttl_hours)).timestamp()),
        "sensor": {},
        "risk": {},
        "ai_detection": {
            "threshold": ai_score_threshold,
            "max_score": None,
            "max_score_type": None,
            "max_score_at": None,
            "above_threshold_count": 0,
            "by_type": {},
        },
        "infra": {},
        "quality": _quality(source_count, expected_count, bucket_start_iso, bucket_end_iso),
        "created_at": created_at_iso,
        "updated_at": created_at_iso,
    }

    if not source_items:
        return item

    sensor_reducers = {name: NumericReducer() for name in SENSOR_METRICS}
    risk_reducers = {name: NumericReducer() for name in RISK_METRICS}
    infra_reducers = {name: NumericReducer() for name in INFRA_METRICS}
    node_infra_reducers = {}
    node_metadata = {}
    ai_reducer = AiReducer(ai_score_threshold)
    seen_sensor = {name: set() for name in SENSOR_METRICS}
    seen_risk = {name: set() for name in RISK_METRICS}
    seen_ai = {name: set() for name in AI_METRICS}
    seen_infra = {name: set() for name in INFRA_METRICS}
    seen_node_infra = {}

    for source in source_items:
        factory_state = source.get("factory_state") or {}
        risk = source.get("risk") or {}
        factory_at = factory_state.get("source_timestamp") or _item_timestamp(source)
        infra_at = (source.get("infra_state") or {}).get("source_timestamp") or _item_timestamp(source)
        factory_in_bucket = _timestamp_in_bucket(factory_at, bucket_start, bucket_end)
        infra_in_bucket = _timestamp_in_bucket(infra_at, bucket_start, bucket_end)

        if factory_in_bucket:
            for metric in SENSOR_METRICS:
                _add_once(sensor_reducers[metric], seen_sensor[metric], factory_state.get(metric), factory_at)
            for metric in AI_METRICS:
                ai_value = _number(factory_state.get(metric))
                if ai_value is not None and factory_at not in seen_ai[metric]:
                    ai_reducer.add(metric, ai_value, factory_at)
                    seen_ai[metric].add(factory_at)

        for metric in RISK_METRICS:
            risk_at = risk.get("calculated_at") or _item_timestamp(source)
            _add_once(risk_reducers[metric], seen_risk[metric], risk.get(metric), risk_at)

        if infra_in_bucket:
            for metric, value in _infra_snapshot_values(source).items():
                _add_once(infra_reducers[metric], seen_infra[metric], value, infra_at)
            _add_node_infra_snapshot(node_infra_reducers, node_metadata, seen_node_infra, source, infra_at)

    item["sensor"] = _summaries(sensor_reducers, SENSOR_METRICS)
    item["risk"] = _summaries(risk_reducers, RISK_METRICS)
    item["infra"] = _summaries(infra_reducers, INFRA_METRICS)
    node_summaries = _node_infra_summaries(node_infra_reducers, node_metadata)
    if node_summaries:
        item["infra"]["nodes"] = node_summaries
    item["ai_detection"] = ai_reducer.summary()
    return item


def _summaries(reducers: dict[str, NumericReducer], units: dict[str, str]) -> dict:
    result = {}
    for metric, reducer in reducers.items():
        summary = reducer.summary(units[metric])
        if summary:
            result[metric] = summary
    return result


def _infra_snapshot_values(source: dict) -> dict:
    nodes = (source.get("infra_state") or {}).get("nodes") or []
    values = {}
    for metric in INFRA_METRICS:
        node_values = [_number(node.get(metric)) for node in nodes if isinstance(node, dict)]
        node_values = [value for value in node_values if value is not None]
        if node_values:
            values[metric] = sum(node_values) / len(node_values)
    return values


def _add_node_infra_snapshot(
    node_infra_reducers: dict,
    node_metadata: dict,
    seen_node_infra: dict,
    source: dict,
    infra_at: str,
):
    nodes = (source.get("infra_state") or {}).get("nodes") or []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = _node_id(node)
        if not node_id:
            continue
        node_metadata.setdefault(node_id, _node_metadata(node, node_id))
        node_reducers = node_infra_reducers.setdefault(node_id, {name: NumericReducer() for name in INFRA_METRICS})
        node_seen = seen_node_infra.setdefault(node_id, {name: set() for name in INFRA_METRICS})
        for metric in INFRA_METRICS:
            _add_once(node_reducers[metric], node_seen[metric], node.get(metric), infra_at)


def _node_infra_summaries(node_infra_reducers: dict, node_metadata: dict) -> list[dict]:
    nodes = []
    for node_id in sorted(node_infra_reducers):
        item = dict(node_metadata.get(node_id) or {"node_id": node_id})
        for metric, reducer in node_infra_reducers[node_id].items():
            summary = reducer.summary(INFRA_METRICS[metric])
            if summary:
                item[metric] = summary
        if any(metric in item for metric in INFRA_METRICS):
            nodes.append(item)
    return nodes


def _node_id(node: dict) -> str:
    return str(node.get("node_id") or node.get("name") or "").strip()


def _node_metadata(node: dict, node_id: str) -> dict:
    result = {"node_id": node_id}
    role = str(node.get("role") or "").strip()
    if role:
        result["role"] = role
    return result


def _quality(source_count: int, expected_count: int, bucket_start_iso: str, bucket_end_iso: str) -> dict:
    missing_count = max(expected_count - source_count, 0)
    return {
        "source_dataset": "DynamoDB HISTORY#STATE",
        "source_count": source_count,
        "expected_count": expected_count,
        "collection_rate": _round(min(source_count / expected_count, 1.0)) if expected_count else 0.0,
        "missing_count": missing_count,
        "is_empty": source_count == 0,
        "is_partial": source_count < expected_count,
        "infra_values_from_snapshot": True,
        "source_window_start_sk": f"HISTORY#STATE#{bucket_start_iso}",
        "source_window_end_sk": f"HISTORY#STATE#{bucket_end_iso}",
    }


def _expected_count(bucket_start, bucket_end, interval_seconds: int) -> int:
    seconds = (bucket_end + timedelta(milliseconds=1) - bucket_start).total_seconds()
    return int(math.ceil(seconds / interval_seconds)) if interval_seconds > 0 else 0


def _item_timestamp(item: dict) -> str:
    return item.get("updated_at") or item.get("sk", "").removeprefix("HISTORY#STATE#")


def _actual_observation_count(source_items: list[dict], bucket_start, bucket_end) -> int:
    count = 0
    for source in source_items:
        factory_at = (source.get("factory_state") or {}).get("source_timestamp") or _item_timestamp(source)
        infra_at = (source.get("infra_state") or {}).get("source_timestamp") or _item_timestamp(source)
        if _timestamp_in_bucket(factory_at, bucket_start, bucket_end) or _timestamp_in_bucket(infra_at, bucket_start, bucket_end):
            count += 1
    return count


def _timestamp_in_bucket(value: str | None, bucket_start, bucket_end) -> bool:
    if not value:
        return False
    try:
        timestamp = parse_utc(value)
    except (TypeError, ValueError):
        return False
    return bucket_start <= timestamp <= bucket_end


def _number(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _add_once(reducer: NumericReducer, seen: set[str], value, at: str):
    number = _number(value)
    if number is None:
        return
    if at in seen:
        return
    reducer.add(number, at)
    seen.add(at)


def _round(value: float) -> float:
    return round(float(value), 4)
