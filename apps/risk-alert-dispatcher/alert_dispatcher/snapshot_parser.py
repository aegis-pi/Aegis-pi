from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotSource:
    source_type: str
    scope: str
    status: str
    key: str


def parse_source(key: str) -> SnapshotSource | None:
    parts = key.split("/")
    if len(parts) < 4 or parts[0] != "processed":
        return None

    if parts[1] == "cloud_infra" and len(parts) >= 3 and parts[2] in {"fast", "slow"}:
        return SnapshotSource(
            source_type=f"cloud_infra_{parts[2]}",
            scope="cloud-infra",
            status=parts[2],
            key=key,
        )

    if len(parts) >= 3 and parts[2] == "state_snapshot":
        return SnapshotSource(
            source_type="factory_state_snapshot",
            scope=parts[1],
            status="state_snapshot",
            key=key,
        )

    return None
