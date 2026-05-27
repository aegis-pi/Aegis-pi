from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import ceil
from statistics import mean
from typing import Iterable


@dataclass
class NumericReducer:
    values: list[float] = field(default_factory=list)

    def add(self, value) -> None:
        if value is None:
            return
        try:
            self.values.append(float(value))
        except (TypeError, ValueError):
            return

    def summary(self, prefix: str) -> dict:
        if not self.values:
            return {
                f"{prefix}_avg": None,
                f"{prefix}_min": None,
                f"{prefix}_max": None,
                f"{prefix}_p05": None,
                f"{prefix}_p95": None,
            }
        values = sorted(self.values)
        return {
            f"{prefix}_avg": round(mean(values), 2),
            f"{prefix}_min": round(values[0], 2),
            f"{prefix}_max": round(values[-1], 2),
            f"{prefix}_p05": round(percentile(values, 5), 2),
            f"{prefix}_p95": round(percentile(values, 95), 2),
        }


def percentile(sorted_values: list[float], percentile_value: int) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = ceil((percentile_value / 100.0) * len(sorted_values))
    return sorted_values[max(0, min(rank - 1, len(sorted_values) - 1))]


def max_gap_seconds(timestamps: Iterable[datetime]) -> int:
    ordered = sorted(timestamps)
    if len(ordered) < 2:
        return 0
    return int(max((b - a).total_seconds() for a, b in zip(ordered, ordered[1:])))

