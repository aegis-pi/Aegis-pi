import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "factory_a_log_adapter.py"
SPEC = importlib.util.spec_from_file_location("factory_a_log_adapter", MODULE_PATH)
adapter_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adapter_module)


class FakeInflux:
    def __init__(self, rows_by_measurement):
        self.rows_by_measurement = rows_by_measurement

    def query(self, query):
        for measurement, rows in self.rows_by_measurement.items():
            if f"FROM {measurement}" in query:
                return rows
        return []


class FakeKubernetes:
    def nodes(self):
        return [
            {
                "metadata": {
                    "name": "master",
                    "labels": {"kubernetes.io/hostname": "master"},
                },
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            },
            {
                "metadata": {
                    "name": "worker-2",
                    "labels": {"kubernetes.io/hostname": "worker2"},
                },
                "status": {"conditions": [{"type": "Ready", "status": "False"}]},
            },
        ]

    def pods(self, namespace):
        pods = {
            "monitoring": [
                self._pod(namespace, "bme280-sensor-abc", "Running", True, 1, "worker-2"),
                self._pod(namespace, "influxdb-0", "Running", True, 0, "master"),
                self._pod(namespace, "prometheus-0", "Pending", False, 0, "master"),
                self._pod(namespace, "grafana-0", "Running", True, 0, "master"),
            ],
            "ai-apps": [
                self._pod(namespace, "safe-edge-integrated-ai-abc", "Running", True, 2, "worker-2"),
                self._pod(namespace, "safe-edge-audio-abc", "Running", False, 3, "worker-2"),
            ],
        }
        return pods.get(namespace, [])

    def _pod(self, namespace, name, phase, ready, restart_count, node_name):
        return {
            "metadata": {
                "namespace": namespace,
                "name": name,
                "creationTimestamp": "2026-05-18T01:00:00Z",
            },
            "spec": {"nodeName": node_name},
            "status": {
                "phase": phase,
                "containerStatuses": [{"ready": ready, "restartCount": restart_count}],
            },
        }


class FakePrometheus:
    def query(self, query):
        if query == "node_uname_info":
            return [
                {
                    "metric": {"instance": "10.10.10.10:9100", "nodename": "master"},
                    "value": [1779840000, "1"],
                },
                {
                    "metric": {"instance": "10.10.10.12:9100", "nodename": "worker-2"},
                    "value": [1779840000, "1"],
                },
            ]
        if "node_cpu_seconds_total" in query:
            return [
                {"metric": {"instance": "10.10.10.10:9100"}, "value": [1779840000, "31.234"]},
                {"metric": {"instance": "10.10.10.12:9100"}, "value": [1779840000, "44.567"]},
            ]
        if "node_memory_MemAvailable_bytes" in query:
            return [
                {"metric": {"instance": "10.10.10.10:9100"}, "value": [1779840000, "55.432"]},
                {"metric": {"instance": "10.10.10.12:9100"}, "value": [1779840000, "63.219"]},
            ]
        if "node_filesystem_avail_bytes" in query:
            return [
                {"metric": {"instance": "10.10.10.10:9100"}, "value": [1779840000, "42.111"]},
                {"metric": {"instance": "10.10.10.12:9100"}, "value": [1779840000, "45.555"]},
            ]
        return []


class FactoryALogAdapterTest(unittest.TestCase):
    def setUp(self):
        self.old_env = os.environ.copy()
        os.environ["AEGIS_FACTORY_ID"] = "factory-a"
        os.environ["AEGIS_DATA_PLANE_INSTANCE_ID"] = "test-adapter"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_factory_state_uses_acoustic_event_label_when_dangerous(self):
        adapter = adapter_module.Adapter()
        adapter.influx = FakeInflux(
            {
                "environment_data": [
                    {
                        "time": "2026-05-18T01:00:00Z",
                        "sample_count": 2,
                        "temperature_celsius_avg": 25.5,
                        "humidity_percent_avg": 42.1,
                        "pressure_hpa_avg": 1008.3,
                        "node": "worker-2",
                        "location": "factory-a",
                    }
                ],
                "ai_detection": [
                    {
                        "time": "2026-05-18T01:00:00Z",
                        "sample_count": 2,
                        "fire_score": 0.0,
                        "fall_score": 0.5,
                        "bend_score": 0.25,
                        "node": "worker-2",
                        "location": "factory-a",
                    }
                ],
                "acoustic_detection": [
                    {
                        "time": "2026-05-18T01:00:00Z",
                        "sample_count": 2,
                        "danger_count": 1,
                        "max_confidence": 0.91,
                        "event_type": "impact",
                        "node": "worker-2",
                        "location": "factory-a",
                    }
                ],
            }
        )

        message = adapter.factory_state()

        self.assertEqual(message["source_type"], "factory_state")
        self.assertEqual(message["node_id"], "worker2")
        self.assertEqual(message["data_plane_instance_id"], "test-adapter")
        self.assertEqual(message["payload"]["sensor"]["sample_count"], 2)
        self.assertEqual(message["payload"]["ai_result"]["abnormal_sound"], "impact")

    def test_factory_state_uses_none_when_acoustic_is_not_dangerous(self):
        adapter = adapter_module.Adapter()
        adapter.influx = FakeInflux(
            {
                "environment_data": [],
                "ai_detection": [],
                "acoustic_detection": [
                    {
                        "sample_count": 2,
                        "danger_count": 0,
                        "max_confidence": 0.2,
                        "event_type": "None",
                        "node": "worker-2",
                    }
                ],
            }
        )

        message = adapter.factory_state()

        self.assertEqual(message["payload"]["ai_result"]["abnormal_sound"], "none")

    def test_infra_state_summarizes_nodes_workloads_and_devices(self):
        adapter = adapter_module.Adapter()
        adapter.k8s = FakeKubernetes()
        adapter.influx = FakeInflux(
            {
                "environment_data": [{"time": "2026-05-18T01:00:01Z"}],
                "ai_detection": [{"time": "2026-05-18T01:00:02Z"}],
                "acoustic_detection": [{"time": "2026-05-18T01:00:03Z"}],
            }
        )

        message = adapter.infra_state()
        payload = message["payload"]
        workloads = {(item["namespace"], item["name"]): item for item in payload["workloads"]}

        self.assertEqual(payload["node_summary"], {"total": 2, "ready": 1, "not_ready": 1})
        self.assertEqual(workloads[("monitoring", "bme280-sensor")]["node_id"], "worker2")
        self.assertTrue(payload["devices"]["bme280"]["available"])
        self.assertFalse(payload["devices"]["microphone"]["available"])

    def test_infra_state_adds_prometheus_node_metrics(self):
        adapter = adapter_module.Adapter()
        adapter.k8s = FakeKubernetes()
        adapter.prometheus = FakePrometheus()
        adapter.influx = FakeInflux(
            {
                "environment_data": [{"time": "2026-05-18T01:00:01Z"}],
                "ai_detection": [{"time": "2026-05-18T01:00:02Z"}],
                "acoustic_detection": [{"time": "2026-05-18T01:00:03Z"}],
            }
        )

        message = adapter.infra_state()
        nodes = {item["node_id"]: item for item in message["payload"]["nodes"]}

        self.assertEqual(nodes["master"]["cpu_usage_percent"], 31.23)
        self.assertEqual(nodes["master"]["memory_usage_percent"], 55.43)
        self.assertEqual(nodes["master"]["disk_usage_percent"], 42.11)
        self.assertEqual(nodes["worker2"]["cpu_usage_percent"], 44.57)
        self.assertEqual(nodes["worker2"]["memory_usage_percent"], 63.22)
        self.assertEqual(nodes["worker2"]["disk_usage_percent"], 45.55)
        self.assertEqual(nodes["master"]["network_reachability"], "ok")

    def test_write_outbox_creates_message_file_once(self):
        adapter = adapter_module.Adapter()
        message = {
            "message_id": "factory-a:factory_state:worker2:2026-05-18T01:00:00Z",
            "source_type": "factory_state",
        }

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp) / "outbox"
            first = adapter.write_outbox(message, outbox)
            second = adapter.write_outbox(message, outbox)

            self.assertEqual(first, second)
            self.assertTrue(first.exists())
            self.assertEqual(json.loads(first.read_text(encoding="utf-8")), message)
            self.assertTrue((outbox / "tmp").is_dir())


if __name__ == "__main__":
    unittest.main()
