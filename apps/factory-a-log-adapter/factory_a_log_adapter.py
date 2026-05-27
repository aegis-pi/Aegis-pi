#!/usr/bin/env python3
"""Build canonical AEGIS JSON from factory-a InfluxDB and Kubernetes state."""

from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_WORKLOADS = (
    "monitoring/bme280-sensor",
    "ai-apps/safe-edge-integrated-ai",
    "ai-apps/safe-edge-audio",
    "monitoring/influxdb",
    "monitoring/prometheus",
    "monitoring/grafana",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, int):
        return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc)

    text = str(value)
    if text.isdigit():
        return datetime.fromtimestamp(int(text) / 1_000_000_000, tz=timezone.utc)

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def normalize_node_id(value: str | None) -> str:
    if not value:
        return "unknown"

    node = value.strip().lower()
    aliases = {
        "worker-1": "worker1",
        "worker-2": "worker2",
        "worker_1": "worker1",
        "worker_2": "worker2",
    }
    return aliases.get(node, node)


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


class InfluxClient:
    def __init__(self, url: str, database: str, timeout_seconds: float = 5.0) -> None:
        self.url = url.rstrip("/")
        self.database = database
        self.timeout_seconds = timeout_seconds

    def query(self, query: str) -> list[dict[str, Any]]:
        params = urllib.parse.urlencode({"db": self.database, "q": query})
        request = urllib.request.Request(f"{self.url}/query?{params}")

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if payload.get("error"):
            raise RuntimeError(payload["error"])

        rows: list[dict[str, Any]] = []
        for result in payload.get("results", []):
            if result.get("error"):
                raise RuntimeError(result["error"])
            for series in result.get("series", []):
                columns = series.get("columns", [])
                tags = series.get("tags", {})
                for values in series.get("values", []):
                    row = dict(zip(columns, values))
                    row.update(tags)
                    rows.append(row)
        return rows


class PrometheusClient:
    def __init__(self, url: str, timeout_seconds: float = 5.0) -> None:
        self.url = url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def query(self, query: str) -> list[dict[str, Any]]:
        params = urllib.parse.urlencode({"query": query})
        request = urllib.request.Request(f"{self.url}/api/v1/query?{params}")

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if payload.get("status") != "success":
            raise RuntimeError(payload.get("error") or "Prometheus query failed")

        return payload.get("data", {}).get("result", [])


class KubernetesClient:
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.host = os.getenv("KUBERNETES_SERVICE_HOST")
        self.port = os.getenv("KUBERNETES_SERVICE_PORT", "443")
        self.token_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
        self.ca_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
        self.namespace_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")

    def available(self) -> bool:
        return bool(self.host and self.token_path.exists())

    def get_json(self, path: str) -> dict[str, Any]:
        if not self.available():
            raise RuntimeError("in-cluster Kubernetes service account is not available")

        token = self.token_path.read_text(encoding="utf-8").strip()
        context = ssl.create_default_context(cafile=str(self.ca_path)) if self.ca_path.exists() else ssl.create_default_context()
        request = urllib.request.Request(
            f"https://{self.host}:{self.port}{path}",
            headers={"Authorization": f"Bearer {token}"},
        )

        with urllib.request.urlopen(request, context=context, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def nodes(self) -> list[dict[str, Any]]:
        try:
            return self.get_json("/api/v1/nodes").get("items", [])
        except Exception:
            return kubectl_json(["get", "nodes", "-o", "json"]).get("items", [])

    def pods(self, namespace: str) -> list[dict[str, Any]]:
        try:
            return self.get_json(f"/api/v1/namespaces/{namespace}/pods").get("items", [])
        except Exception:
            return kubectl_json(["-n", namespace, "get", "pods", "-o", "json"]).get("items", [])


def kubectl_json(args: list[str]) -> dict[str, Any]:
    output = subprocess.check_output(["kubectl", *args], text=True, stderr=subprocess.DEVNULL)
    return json.loads(output)


class Adapter:
    def __init__(self) -> None:
        self.factory_id = os.getenv("AEGIS_FACTORY_ID", "factory-a")
        self.environment_type = os.getenv("AEGIS_ENVIRONMENT_TYPE", "physical-rpi")
        self.input_module_type = os.getenv("AEGIS_INPUT_MODULE_TYPE", "sensor")
        self.influx = InfluxClient(
            os.getenv("AEGIS_INFLUXDB_URL", "http://influxdb-svc.monitoring.svc.cluster.local:8086"),
            os.getenv("AEGIS_INFLUXDB_DATABASE", "safe_edge_db"),
            float(os.getenv("AEGIS_HTTP_TIMEOUT_SECONDS", "5")),
        )
        self.prometheus = PrometheusClient(
            os.getenv("AEGIS_PROMETHEUS_URL", "http://prometheus-svc.monitoring.svc.cluster.local:9090"),
            float(os.getenv("AEGIS_HTTP_TIMEOUT_SECONDS", "5")),
        )
        self.k8s = KubernetesClient(timeout_seconds=float(os.getenv("AEGIS_K8S_TIMEOUT_SECONDS", "5")))
        self.window_seconds = int(os.getenv("AEGIS_FACTORY_STATE_WINDOW_SECONDS", "3"))
        self.factory_state_interval_seconds = int(os.getenv("AEGIS_FACTORY_STATE_INTERVAL_SECONDS", "3"))
        self.infra_state_interval_seconds = int(os.getenv("AEGIS_INFRA_STATE_INTERVAL_SECONDS", "20"))
        self.fallback_limit = int(os.getenv("AEGIS_INFLUXDB_FALLBACK_SAMPLE_LIMIT", "5"))
        self.data_plane_instance_id = os.getenv(
            "AEGIS_DATA_PLANE_INSTANCE_ID",
            f"factory-a-log-adapter-{socket.gethostname()}",
        )

    def factory_state(self) -> dict[str, Any]:
        collected_at = utc_now()
        sensor_rows = self._aggregate_environment()
        ai_rows = self._aggregate_ai()
        acoustic_rows = self._aggregate_acoustic()

        source_times = [
            parse_time(row.get("time")) for row in [*sensor_rows, *ai_rows, *acoustic_rows]
        ]
        source_timestamp = max([item for item in source_times if item is not None], default=collected_at)

        node_id = self._dominant_node(sensor_rows, ai_rows, acoustic_rows)
        message_id = f"{self.factory_id}:factory_state:{node_id}:{format_utc(source_timestamp)}"

        sensor = self._sensor_payload(sensor_rows)
        ai_result = self._ai_payload(ai_rows)
        ai_result["abnormal_sound"] = self._abnormal_sound(acoustic_rows)

        return self._message(
            message_id=message_id,
            node_id=node_id,
            source_type="factory_state",
            source_timestamp=source_timestamp,
            payload={
                "aggregation_window_seconds": self.window_seconds,
                "sensor": sensor,
                "ai_result": ai_result,
            },
        )

    def infra_state(self) -> dict[str, Any]:
        collected_at = utc_now()
        node_metrics = self._node_metrics()
        nodes = [self._node_payload(item, node_metrics) for item in self.k8s.nodes()]
        workloads = self._workload_payloads()
        devices = self._device_payloads(workloads)
        message_id = f"{self.factory_id}:infra_state:cluster:{format_utc(collected_at)}"

        ready_nodes = sum(1 for item in nodes if item["ready"])
        running_workloads = sum(1 for item in workloads if item["status"] == "Running" and item["ready"])

        return self._message(
            message_id=message_id,
            node_id="cluster",
            source_type="infra_state",
            source_timestamp=collected_at,
            payload={
                "heartbeat": {
                    "agent_status": "alive",
                    "last_spool_write_status": "unknown",
                    "last_spool_write_at": None,
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
                self._write_one("infra_state", outbox_dir)
                next_infra_state = now + self.infra_state_interval_seconds
            sleep_until.append(next_infra_state)

            delay = max(min(sleep_until) - time.monotonic(), 0.1)
            time.sleep(delay)

    def _write_one(self, source_type: str, outbox_dir: Path) -> None:
        try:
            if source_type == "factory_state":
                message = self.factory_state()
            elif source_type == "infra_state":
                message = self.infra_state()
            else:
                raise ValueError(f"unsupported source_type: {source_type}")
            path = self.write_outbox(message, outbox_dir)
            print(f"wrote {path}", flush=True)
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

    def _aggregate_environment(self) -> list[dict[str, Any]]:
        query = (
            "SELECT count(temperature) AS sample_count, "
            "mean(temperature) AS temperature_celsius_avg, "
            "mean(humidity) AS humidity_percent_avg, "
            "mean(pressure) AS pressure_hpa_avg "
            f"FROM environment_data WHERE time > now() - {self.window_seconds}s GROUP BY node,location"
        )
        rows = self.influx.query(query)
        if rows:
            return rows

        rows = self.influx.query(f"SELECT * FROM environment_data ORDER BY time DESC LIMIT {self.fallback_limit}")
        return [self._aggregate_rows(rows, ("temperature", "humidity", "pressure"))] if rows else []

    def _aggregate_ai(self) -> list[dict[str, Any]]:
        query = (
            "SELECT count(fire_detected) AS sample_count, "
            "mean(fire_detected) AS fire_score, "
            "mean(fallen_detected) AS fall_score, "
            "mean(bending_detected) AS bend_score "
            f"FROM ai_detection WHERE time > now() - {self.window_seconds}s GROUP BY node,location"
        )
        rows = self.influx.query(query)
        if rows:
            return rows

        rows = self.influx.query(f"SELECT * FROM ai_detection ORDER BY time DESC LIMIT {self.fallback_limit}")
        return [self._aggregate_rows(rows, ("fire_detected", "fallen_detected", "bending_detected"))] if rows else []

    def _aggregate_acoustic(self) -> list[dict[str, Any]]:
        query = (
            "SELECT count(confidence) AS sample_count, "
            "sum(is_danger) AS danger_count, "
            "max(confidence) AS max_confidence "
            f"FROM acoustic_detection WHERE time > now() - {self.window_seconds}s GROUP BY event_type,node,location"
        )
        rows = self.influx.query(query)
        if rows:
            return rows

        rows = self.influx.query(f"SELECT * FROM acoustic_detection ORDER BY time DESC LIMIT {self.fallback_limit}")
        if not rows:
            return []
        return [self._aggregate_acoustic_rows(rows)]

    def _aggregate_rows(self, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
        row: dict[str, Any] = {
            "time": max((item.get("time") for item in rows if item.get("time")), default=None),
            "sample_count": len(rows),
            "node": rows[0].get("node"),
            "location": rows[0].get("location"),
        }
        for field in fields:
            values = [safe_float(item.get(field)) for item in rows]
            clean = [item for item in values if item is not None]
            row[field] = sum(clean) / len(clean) if clean else None
        return row

    def _aggregate_acoustic_rows(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        danger_count = sum(safe_int(item.get("is_danger")) for item in rows)
        confidences = [safe_float(item.get("confidence")) for item in rows]
        clean_confidences = [item for item in confidences if item is not None]
        dangerous = [item for item in rows if safe_int(item.get("is_danger")) > 0]
        label_source = dangerous[0] if dangerous else rows[0]
        return {
            "time": max((item.get("time") for item in rows if item.get("time")), default=None),
            "sample_count": len(rows),
            "danger_count": danger_count,
            "max_confidence": max(clean_confidences) if clean_confidences else None,
            "event_type": label_source.get("event_type"),
            "node": label_source.get("node"),
            "location": label_source.get("location"),
        }

    def _sensor_payload(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        row = rows[0] if rows else {}
        return {
            "sample_count": safe_int(row.get("sample_count")),
            "temperature_celsius_avg": safe_float(row.get("temperature_celsius_avg", row.get("temperature"))),
            "humidity_percent_avg": safe_float(row.get("humidity_percent_avg", row.get("humidity"))),
            "pressure_hpa_avg": safe_float(row.get("pressure_hpa_avg", row.get("pressure"))),
        }

    def _ai_payload(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        row = rows[0] if rows else {}
        return {
            "sample_count": safe_int(row.get("sample_count")),
            "fire_score": safe_float(row.get("fire_score", row.get("fire_detected"))),
            "fall_score": safe_float(row.get("fall_score", row.get("fallen_detected"))),
            "bend_score": safe_float(row.get("bend_score", row.get("bending_detected"))),
        }

    def _abnormal_sound(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "none"

        best = sorted(
            rows,
            key=lambda item: (safe_int(item.get("danger_count")), safe_float(item.get("max_confidence")) or 0.0),
            reverse=True,
        )[0]

        if safe_int(best.get("danger_count")) <= 0:
            return "none"

        event_type = str(best.get("event_type") or "").strip()
        if not event_type or event_type.lower() == "none":
            return "abnormal_sound"
        return event_type

    def _dominant_node(self, *row_groups: list[dict[str, Any]]) -> str:
        for rows in row_groups:
            for row in rows:
                node = normalize_node_id(row.get("node"))
                if node != "unknown":
                    return node
        return "cluster"

    def _node_payload(self, item: dict[str, Any], node_metrics: dict[str, dict[str, float | None]] | None = None) -> dict[str, Any]:
        name = normalize_node_id(item.get("metadata", {}).get("name"))
        conditions = item.get("status", {}).get("conditions", [])
        ready = any(cond.get("type") == "Ready" and cond.get("status") == "True" for cond in conditions)
        metrics = (node_metrics or {}).get(name, {})
        role = "unknown"
        labels = item.get("metadata", {}).get("labels", {})
        if labels.get("kubernetes.io/hostname") == "worker2" or name == "worker2":
            role = "sensor-ai-audio-preferred"
        elif name == "worker1":
            role = "failover-standby"
        elif name == "master":
            role = "control-plane"
        return {
            "node_id": name,
            "role": role,
            "ready": ready,
            "cpu_usage_percent": metrics.get("cpu_usage_percent"),
            "memory_usage_percent": metrics.get("memory_usage_percent"),
            "disk_usage_percent": metrics.get("disk_usage_percent"),
            "network_reachability": "ok" if ready else "not_ready",
        }

    def _node_metrics(self) -> dict[str, dict[str, float | None]]:
        try:
            instance_to_node = self._prometheus_instance_to_node()
            metrics: dict[str, dict[str, float | None]] = {}
            for field, query in {
                "cpu_usage_percent": '100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[2m])))',
                "memory_usage_percent": "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))",
                "disk_usage_percent": '100 * (1 - (node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay|aufs|squashfs"} / node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay|aufs|squashfs"}))',
            }.items():
                for result in self.prometheus.query(query):
                    node_id = self._node_id_from_prometheus_metric(result.get("metric", {}), instance_to_node)
                    value = self._prometheus_value(result)
                    if node_id and value is not None:
                        metrics.setdefault(node_id, {})[field] = round(max(min(value, 100.0), 0.0), 2)
            return metrics
        except Exception as exc:
            print(f"failed to read Prometheus node metrics: {exc}", file=sys.stderr, flush=True)
            return {}

    def _prometheus_instance_to_node(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        try:
            for result in self.prometheus.query("node_uname_info"):
                labels = result.get("metric", {})
                instance = labels.get("instance")
                node = labels.get("nodename") or labels.get("node") or labels.get("kubernetes_node")
                if instance and node:
                    mapping[str(instance)] = normalize_node_id(str(node))
        except Exception:
            return {}
        return mapping

    def _node_id_from_prometheus_metric(self, labels: dict[str, Any], instance_to_node: dict[str, str]) -> str | None:
        for key in ("node", "kubernetes_node", "nodename"):
            if labels.get(key):
                return normalize_node_id(str(labels[key]))

        instance = labels.get("instance")
        if not instance:
            return None
        if str(instance) in instance_to_node:
            return instance_to_node[str(instance)]

        host = str(instance).split(":", 1)[0]
        return normalize_node_id(host)

    def _prometheus_value(self, result: dict[str, Any]) -> float | None:
        value = result.get("value")
        if not isinstance(value, list) or len(value) < 2:
            return None
        return safe_float(value[1])

    def _workload_payloads(self) -> list[dict[str, Any]]:
        requested = os.getenv("AEGIS_WORKLOADS", ",".join(DEFAULT_WORKLOADS)).split(",")
        by_namespace: dict[str, list[str]] = {}
        for value in requested:
            value = value.strip()
            if not value or "/" not in value:
                continue
            namespace, name = value.split("/", 1)
            by_namespace.setdefault(namespace, []).append(name)

        payloads: list[dict[str, Any]] = []
        for namespace, names in by_namespace.items():
            pods = self.k8s.pods(namespace)
            for name in names:
                selected = [pod for pod in pods if pod.get("metadata", {}).get("name", "").startswith(f"{name}-")]
                payloads.append(self._workload_payload(namespace, name, selected))
        return payloads

    def _workload_payload(self, namespace: str, name: str, pods: list[dict[str, Any]]) -> dict[str, Any]:
        if not pods:
            return {
                "namespace": namespace,
                "name": name,
                "status": "NotFound",
                "ready": False,
                "restart_count": 0,
                "node_id": "unknown",
            }

        pod = sorted(pods, key=lambda item: item.get("metadata", {}).get("creationTimestamp", ""), reverse=True)[0]
        statuses = pod.get("status", {}).get("containerStatuses", [])
        ready = bool(statuses) and all(item.get("ready") for item in statuses)
        restart_count = sum(safe_int(item.get("restartCount")) for item in statuses)
        return {
            "namespace": namespace,
            "name": name,
            "status": pod.get("status", {}).get("phase", "unknown"),
            "ready": ready,
            "restart_count": restart_count,
            "node_id": normalize_node_id(pod.get("spec", {}).get("nodeName")),
        }

    def _device_payloads(self, workloads: list[dict[str, Any]]) -> dict[str, Any]:
        workload_map = {item["name"]: item for item in workloads}
        return {
            "bme280": self._device_from_measurement(workload_map.get("bme280-sensor"), "environment_data"),
            "camera": self._device_from_measurement(workload_map.get("safe-edge-integrated-ai"), "ai_detection"),
            "microphone": self._device_from_measurement(workload_map.get("safe-edge-audio"), "acoustic_detection"),
        }

    def _device_from_measurement(self, workload: dict[str, Any] | None, measurement: str) -> dict[str, Any]:
        last_seen = self._last_measurement_time(measurement)
        return {
            "available": bool(workload and workload.get("status") == "Running" and workload.get("ready")),
            "last_seen_at": format_utc(last_seen) if last_seen else None,
        }

    def _last_measurement_time(self, measurement: str) -> datetime | None:
        try:
            rows = self.influx.query(f"SELECT * FROM {measurement} ORDER BY time DESC LIMIT 1")
        except Exception:
            return None
        if not rows:
            return None
        return parse_time(rows[0].get("time"))


def build_messages(adapter: Adapter, mode: str) -> list[dict[str, Any]]:
    if mode == "factory_state":
        return [adapter.factory_state()]
    if mode == "infra_state":
        return [adapter.infra_state()]
    return [adapter.factory_state(), adapter.infra_state()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create AEGIS canonical JSON files from factory-a local state.")
    parser.add_argument("--once", choices=("factory_state", "infra_state", "all"), default="all")
    parser.add_argument("--loop", action="store_true", help="Continuously write factory_state and infra_state files.")
    parser.add_argument("--outbox-dir", default=os.getenv("AEGIS_OUTBOX_DIR", "/var/lib/aegis/outbox"))
    parser.add_argument("--no-write", action="store_true", help="Print JSON without writing outbox files.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON to stdout.")
    args = parser.parse_args()

    adapter = Adapter()
    outbox_dir = Path(args.outbox_dir)

    if args.loop:
        if args.no_write:
            parser.error("--loop cannot be used with --no-write")
        adapter.run_loop(outbox_dir)
        return 0

    messages = build_messages(adapter, args.once)

    for message in messages:
        if args.no_write:
            print(json.dumps(message, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
            continue
        path = adapter.write_outbox(message, outbox_dir)
        print(f"wrote {path}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
