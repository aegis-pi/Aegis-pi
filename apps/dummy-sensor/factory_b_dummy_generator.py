#!/usr/bin/env python3
"""Generate factory-b dummy AEGIS canonical JSON into a local outbox."""

from __future__ import annotations

import argparse
import json
import os
import random
import socket
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from k8s_state import KubernetesStateReader, build_workload_payloads


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def env_list(name: str) -> set[str]:
    value = os.getenv(name, "")
    return {item.strip() for item in value.split(",") if item.strip()}


class RoundRobinEventSchedule:
    def __init__(self, rng: random.Random, events: list[str], min_seconds: float, max_seconds: float) -> None:
        self.rng = rng
        self.events = events
        self.min_seconds = min_seconds
        self.max_seconds = max(max_seconds, min_seconds)
        self.index = 0
        self.next_due = time.monotonic() + self._next_interval()

    def due_event(self, now: float | None = None) -> str | None:
        if not self.events:
            return None
        if now is None:
            now = time.monotonic()
        if now < self.next_due:
            return None
        event = self.events[self.index % len(self.events)]
        self.index += 1
        self.next_due = now + self._next_interval()
        return event

    def _next_interval(self) -> float:
        if self.max_seconds <= 0:
            return 0.0
        return self.rng.uniform(self.min_seconds, self.max_seconds)


class FactoryBDummyGenerator:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.factory_id = os.getenv("AEGIS_FACTORY_ID", "factory-b")
        self.environment_type = os.getenv("AEGIS_ENVIRONMENT_TYPE", "vm-mac")
        self.input_module_type = os.getenv("AEGIS_INPUT_MODULE_TYPE", "dummy")
        self.worker_node_id = os.getenv("AEGIS_WORKER_NODE_ID", "worker1")
        self.master_node_id = os.getenv("AEGIS_MASTER_NODE_ID", "master")
        self.kubernetes_version = os.getenv("AEGIS_K3S_VERSION", "unknown")
        self.data_plane_instance_id = os.getenv(
            "AEGIS_DATA_PLANE_INSTANCE_ID",
            f"factory-b-dummy-generator-{socket.gethostname()}",
        )
        self.window_seconds = env_int("AEGIS_FACTORY_STATE_WINDOW_SECONDS", 3)
        self.factory_state_interval_seconds = env_int("AEGIS_FACTORY_STATE_INTERVAL_SECONDS", 3)
        self.infra_state_interval_seconds = env_int("AEGIS_INFRA_STATE_INTERVAL_SECONDS", 20)
        self.sequence_file = Path(os.getenv("AEGIS_SEQUENCE_FILE", "/var/lib/aegis/factory-b-publish-sequence"))
        self.k8s = KubernetesStateReader(timeout_seconds=env_float("AEGIS_K8S_TIMEOUT_SECONDS", 5.0))

        self.temperature_baseline = env_float("AEGIS_DUMMY_TEMPERATURE_BASELINE", 24.5)
        self.temperature_jitter = env_float("AEGIS_DUMMY_TEMPERATURE_JITTER", 3.0)
        self.humidity_baseline = env_float("AEGIS_DUMMY_HUMIDITY_BASELINE", 45.0)
        self.humidity_jitter = env_float("AEGIS_DUMMY_HUMIDITY_JITTER", 8.0)
        self.pressure_baseline = env_float("AEGIS_DUMMY_PRESSURE_BASELINE", 1013.5)
        self.pressure_jitter = env_float("AEGIS_DUMMY_PRESSURE_JITTER", 1.5)
        self.scenario = os.getenv("AEGIS_DUMMY_SCENARIO", "normal").strip().lower() or "normal"
        self.scenario_down_nodes = env_list("AEGIS_DUMMY_SCENARIO_DOWN_NODES")
        self.ai_event_schedule = RoundRobinEventSchedule(
            self.rng,
            ["ai_warning"],
            env_float("AEGIS_DUMMY_AI_EVENT_MIN_SECONDS", 25 * 60),
            env_float("AEGIS_DUMMY_AI_EVENT_MAX_SECONDS", 30 * 60),
        )
        self.sensor_event_schedule = RoundRobinEventSchedule(
            self.rng,
            ["temperature_high", "humidity_high", "pressure_high", "pressure_low"],
            env_float("AEGIS_DUMMY_SENSOR_EVENT_MIN_SECONDS", 6 * 60),
            env_float("AEGIS_DUMMY_SENSOR_EVENT_MAX_SECONDS", 10 * 60),
        )
        self.sensor_event_hold_seconds = env_float("AEGIS_DUMMY_SENSOR_EVENT_HOLD_SECONDS", 30.0)
        self.active_sensor_event: str | None = None
        self.active_sensor_event_until = 0.0
        self.infra_event_schedule = RoundRobinEventSchedule(
            self.rng,
            ["storage_warning", "device_unavailable", "pods_partial", "nodes_partial"],
            env_float("AEGIS_DUMMY_INFRA_EVENT_MIN_SECONDS", 5 * 60),
            env_float("AEGIS_DUMMY_INFRA_EVENT_MAX_SECONDS", 8 * 60),
        )
        self.pipeline_gap_schedule = RoundRobinEventSchedule(
            self.rng,
            ["pipeline_warning_gap"],
            env_float("AEGIS_DUMMY_PIPELINE_GAP_EVENT_MIN_SECONDS", 12 * 60),
            env_float("AEGIS_DUMMY_PIPELINE_GAP_EVENT_MAX_SECONDS", 18 * 60),
        )

    def factory_state(self) -> dict[str, Any]:
        source_timestamp = utc_now()
        timestamp = format_utc(source_timestamp)
        sensor = {
            "sample_count": 1,
            "temperature_celsius_avg": self._jitter(self.temperature_baseline, self.temperature_jitter),
            "humidity_percent_avg": self._jitter(self.humidity_baseline, self.humidity_jitter),
            "pressure_hpa_avg": self._jitter(self.pressure_baseline, self.pressure_jitter),
        }
        sensor_event = self._sensor_event()
        if sensor_event:
            self._apply_sensor_event(sensor, sensor_event)

        ai_result = self._ai_result(self.ai_event_schedule.due_event())

        return self._message(
            message_id=f"{self.factory_id}:factory_state:{self.worker_node_id}:{timestamp}",
            node_id=self.worker_node_id,
            source_type="factory_state",
            source_timestamp=source_timestamp,
            payload={
                "aggregation_window_seconds": self.window_seconds,
                "sensor": sensor,
                "ai_result": ai_result,
            },
        )

    def infra_state(self) -> dict[str, Any]:
        source_timestamp = utc_now()
        timestamp = format_utc(source_timestamp)
        sequence = self._next_sequence()
        nodes, workloads, source = self._cluster_state()
        devices = {
            "bme280": {"available": True, "last_seen_at": timestamp},
            "camera": {"available": True, "last_seen_at": timestamp},
            "microphone": {"available": True, "last_seen_at": timestamp},
        }
        self._apply_infra_event(nodes, workloads, devices, self.infra_event_schedule.due_event(), timestamp)
        self._apply_scenario(nodes, workloads)
        ready_nodes = sum(1 for item in nodes if item["ready"])
        running_workloads = sum(1 for item in workloads if item["status"] == "Running" and item["ready"])

        return self._message(
            message_id=f"{self.factory_id}:infra_state:cluster:{timestamp}",
            node_id="cluster",
            source_type="infra_state",
            source_timestamp=source_timestamp,
            payload={
                "heartbeat": {
                    "agent_status": "alive",
                    "last_spool_write_status": "unknown",
                    "last_spool_write_at": None,
                    "publish_sequence": sequence,
                    "cluster_state_source": source,
                    "dummy_scenario": self.scenario,
                },
                "node_summary": {
                    "total": len(nodes),
                    "ready": ready_nodes,
                    "not_ready": max(len(nodes) - ready_nodes, 0),
                },
                "nodes": nodes,
                "workload_summary": {
                    "total": len(workloads),
                    "running": running_workloads,
                    "not_running": max(len(workloads) - running_workloads, 0),
                },
                "workloads": workloads,
                "devices": devices,
            },
        )

    def write_outbox(self, message: dict[str, Any], outbox_dir: Path) -> Path:
        outbox_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = outbox_dir / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        target = outbox_dir / f"{message['message_id']}.json"
        if target.exists():
            return target

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=tmp_dir,
            prefix=f"{message['message_id']}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(message, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            tmp_path = Path(handle.name)

        tmp_path.replace(target)
        target.chmod(0o640)
        return target

    def run_loop(self, outbox_dir: Path) -> None:
        next_factory_state = 0.0
        next_infra_state = 0.0
        while True:
            now = time.monotonic()
            sleep_until: list[float] = []
            if now >= next_factory_state:
                self._write_one("factory_state", outbox_dir)
                next_factory_state = now + self.factory_state_interval_seconds
            sleep_until.append(next_factory_state)
            if now >= next_infra_state:
                gap_seconds = self._pipeline_gap_seconds(self.pipeline_gap_schedule.due_event(now))
                if gap_seconds:
                    next_infra_state = now + gap_seconds
                else:
                    self._write_one("infra_state", outbox_dir)
                    next_infra_state = now + self.infra_state_interval_seconds
            sleep_until.append(next_infra_state)
            time.sleep(max(min(sleep_until) - time.monotonic(), 0.1))

    def _write_one(self, source_type: str, outbox_dir: Path) -> None:
        try:
            message = self.factory_state() if source_type == "factory_state" else self.infra_state()
            print(f"wrote {self.write_outbox(message, outbox_dir)}", flush=True)
        except Exception as exc:
            print(f"failed to write {source_type}: {exc}", file=sys.stderr, flush=True)

    def _message(
        self,
        *,
        message_id: str,
        node_id: str,
        source_type: str,
        source_timestamp: datetime,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": "0.1.0",
            "message_id": message_id,
            "factory_id": self.factory_id,
            "node_id": node_id,
            "environment_type": self.environment_type,
            "input_module_type": self.input_module_type,
            "source_type": source_type,
            "source_timestamp": format_utc(source_timestamp),
            "published_at": format_utc(utc_now()),
            "data_plane_instance_id": self.data_plane_instance_id,
            "payload": payload,
        }

    def _jitter(self, baseline: float, jitter: float) -> float:
        return round(baseline + self.rng.uniform(-jitter, jitter), 2)

    def _anomaly_score(self) -> float:
        return self.rng.randint(5, 8) / 10

    def _ai_result(self, event: str | None) -> dict[str, Any]:
        result = {
            "sample_count": 1,
            "fire_score": 0.0,
            "fall_score": 0.0,
            "bend_score": 0.0,
            "abnormal_sound": "none",
        }
        if not event:
            return result

        score_fields = ["fire_score", "fall_score", "bend_score"]
        selected = self.rng.sample(score_fields, self.rng.randint(1, 2))
        for field in selected:
            result[field] = self._anomaly_score()
        result["abnormal_sound"] = "brief lab impact"
        return result

    def _apply_sensor_event(self, sensor: dict[str, Any], event: str) -> None:
        if event == "temperature_high":
            sensor["temperature_celsius_avg"] = round(self.rng.uniform(39.0, 45.0), 2)
        elif event == "humidity_high":
            sensor["humidity_percent_avg"] = round(self.rng.uniform(88.0, 96.0), 2)
        elif event == "pressure_high":
            sensor["pressure_hpa_avg"] = round(self.rng.uniform(1055.0, 1075.0), 2)
        elif event == "pressure_low":
            sensor["pressure_hpa_avg"] = round(self.rng.uniform(940.0, 960.0), 2)

    def _sensor_event(self) -> str | None:
        now = time.monotonic()
        if self.active_sensor_event and now < self.active_sensor_event_until:
            return self.active_sensor_event

        event = self.sensor_event_schedule.due_event(now)
        if not event:
            return None

        self.active_sensor_event = event
        self.active_sensor_event_until = now + max(self.sensor_event_hold_seconds, 0.0)
        return event

    def _apply_infra_event(
        self,
        nodes: list[dict[str, Any]],
        workloads: list[dict[str, Any]],
        devices: dict[str, Any],
        event: str | None,
        timestamp: str,
    ) -> None:
        if event == "storage_warning":
            nodes[-1]["disk_usage_percent"] = round(self.rng.uniform(76.0, 84.0), 2)
        elif event == "device_unavailable":
            device = self.rng.choice(["camera", "microphone"])
            devices[device] = {"available": False, "last_seen_at": timestamp}
        elif event == "pods_partial" and workloads:
            workloads[-1]["ready"] = False
            workloads[-1]["status"] = "CrashLoopBackOff"
            workloads[-1]["restart_count"] = self.rng.randint(1, 4)
        elif event == "nodes_partial" and nodes:
            nodes[-1]["ready"] = False
            nodes[-1]["network_reachability"] = "not_ready"

    def _pipeline_gap_seconds(self, event: str | None) -> float | None:
        if event == "pipeline_warning_gap":
            return self.rng.uniform(75.0, 105.0)
        return None

    def _node(self, node_id: str, role: str, cpu: float, memory: float, disk: float) -> dict[str, Any]:
        return {
            "node_id": node_id,
            "role": role,
            "ready": True,
            "cpu_usage_percent": self._jitter(cpu, 2.0),
            "memory_usage_percent": self._jitter(memory, 4.0),
            "disk_usage_percent": self._jitter(disk, 2.0),
            "network_reachability": "ok",
        }

    def _workload(self, namespace: str, name: str, node_id: str) -> dict[str, Any]:
        return {
            "namespace": namespace,
            "name": name,
            "status": "Running",
            "ready": True,
            "restart_count": 0,
            "node_id": node_id,
        }

    def _cluster_state(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
        mode = os.getenv("AEGIS_CLUSTER_STATE_MODE", "synthetic")
        if mode == "kubernetes":
            try:
                workloads = build_workload_payloads(self.k8s)
            except Exception as exc:
                print(f"falling back to synthetic workloads: {exc}", file=sys.stderr, flush=True)
            else:
                return self._fixed_ready_nodes(), workloads, "kubernetes-workloads"
        return [
            self._node(self.master_node_id, "control-plane", 7.0, 32.0, 24.0),
            self._node(self.worker_node_id, "worker", 10.0, 36.0, 25.0),
        ], [
            self._workload("ai-apps", "dummy-data-generator", self.worker_node_id),
            self._workload("ai-apps", "edge-iot-publisher", self.worker_node_id),
        ], "synthetic"

    def _fixed_ready_nodes(self) -> list[dict[str, Any]]:
        return [
            self._node(self.master_node_id, "control-plane", 7.0, 32.0, 24.0),
            self._node(self.worker_node_id, "worker", 10.0, 36.0, 25.0),
        ]

    def _apply_scenario(self, nodes: list[dict[str, Any]], workloads: list[dict[str, Any]]) -> None:
        if self.scenario not in {"node_down", "nodes_down"}:
            return

        down_nodes = self.scenario_down_nodes or {self.worker_node_id}
        for node in nodes:
            if node.get("node_id") in down_nodes:
                node["ready"] = False
                node["network_reachability"] = "not_ready"

        for workload in workloads:
            if workload.get("node_id") in down_nodes:
                workload["ready"] = False
                workload["status"] = "NodeUnavailable"

    def _next_sequence(self) -> int:
        try:
            current = int(self.sequence_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            current = 0
        current += 1
        try:
            self.sequence_file.parent.mkdir(parents=True, exist_ok=True)
            self.sequence_file.write_text(f"{current}\n", encoding="utf-8")
        except OSError:
            pass
        return current


def build_messages(generator: FactoryBDummyGenerator, mode: str) -> list[dict[str, Any]]:
    if mode == "factory_state":
        return [generator.factory_state()]
    if mode == "infra_state":
        return [generator.infra_state()]
    return [generator.factory_state(), generator.infra_state()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create factory-b dummy AEGIS canonical JSON files.")
    parser.add_argument("--once", choices=("factory_state", "infra_state", "all"), default="all")
    parser.add_argument("--loop", action="store_true", help="Continuously write factory_state and infra_state files.")
    parser.add_argument("--outbox-dir", default=os.getenv("AEGIS_OUTBOX_DIR", "/var/lib/aegis/outbox"))
    parser.add_argument("--no-write", action="store_true", help="Print JSON without writing outbox files.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON to stdout.")
    args = parser.parse_args()

    generator = FactoryBDummyGenerator()
    outbox_dir = Path(args.outbox_dir)

    if args.loop:
        if args.no_write:
            parser.error("--loop cannot be used with --no-write")
        generator.run_loop(outbox_dir)
        return 0

    for message in build_messages(generator, args.once):
        if args.no_write:
            print(json.dumps(message, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
            continue
        print(f"wrote {generator.write_outbox(message, outbox_dir)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
