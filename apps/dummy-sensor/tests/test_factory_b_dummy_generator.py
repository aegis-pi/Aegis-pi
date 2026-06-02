import importlib.util
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "factory_b_dummy_generator.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("factory_b_dummy_generator", MODULE_PATH)
generator_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator_module)


class FactoryBDummyGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.old_env = os.environ.copy()
        os.environ["AEGIS_CLUSTER_STATE_MODE"] = "synthetic"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_factory_state_uses_factory_b_stable_lab_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(1))

            message = generator.factory_state()

            self.assertEqual(message["factory_id"], "factory-b")
            self.assertEqual(message["node_id"], "worker1")
            self.assertEqual(message["environment_type"], "vm-mac")
            self.assertEqual(message["input_module_type"], "dummy")
            self.assertEqual(message["source_type"], "factory_state")
            self.assertIn("data_plane_instance_id", message)
            self.assertEqual(message["payload"]["aggregation_window_seconds"], 3)
            self.assertIn("temperature_celsius_avg", message["payload"]["sensor"])

    def test_infra_state_is_two_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(2))

            message = generator.infra_state()

            self.assertEqual([node["node_id"] for node in message["payload"]["nodes"]], ["master", "worker1"])
            self.assertEqual(message["payload"]["node_summary"], {"total": 2, "ready": 2, "not_ready": 0})
            self.assertEqual(message["payload"]["heartbeat"]["agent_status"], "alive")

    def test_node_down_requires_explicit_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            os.environ["AEGIS_DUMMY_SCENARIO"] = "node_down"
            os.environ["AEGIS_DUMMY_SCENARIO_DOWN_NODES"] = "worker1"
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(2))

            message = generator.infra_state()

            self.assertEqual(message["payload"]["node_summary"], {"total": 2, "ready": 1, "not_ready": 1})
            worker = next(node for node in message["payload"]["nodes"] if node["node_id"] == "worker1")
            self.assertFalse(worker["ready"])
            self.assertEqual(worker["network_reachability"], "not_ready")
            self.assertEqual(message["payload"]["heartbeat"]["dummy_scenario"], "node_down")

    def test_default_factory_state_does_not_emit_ai_every_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(3))

            messages = [generator.factory_state() for _ in range(5)]

            for message in messages:
                ai = message["payload"]["ai_result"]
                self.assertEqual(ai["fire_score"], 0.0)
                self.assertEqual(ai["fall_score"], 0.0)
                self.assertEqual(ai["bend_score"], 0.0)
                self.assertEqual(ai["abnormal_sound"], "none")

    def test_ai_event_scores_use_tenth_steps_in_expected_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            os.environ["AEGIS_DUMMY_AI_EVENT_MIN_SECONDS"] = "0"
            os.environ["AEGIS_DUMMY_AI_EVENT_MAX_SECONDS"] = "0"
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(4))

            ai = generator.factory_state()["payload"]["ai_result"]

            scores = [ai["fire_score"], ai["fall_score"], ai["bend_score"]]
            active_scores = [score for score in scores if score > 0]
            self.assertGreaterEqual(len(active_scores), 1)
            self.assertLess(len(active_scores), 3)
            for score in active_scores:
                self.assertGreaterEqual(score, 0.5)
                self.assertLessEqual(score, 1.0)
                self.assertAlmostEqual(score * 10, round(score * 10))

    def test_sensor_round_robin_can_emit_risk_spikes(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            os.environ["AEGIS_DUMMY_SENSOR_EVENT_MIN_SECONDS"] = "0"
            os.environ["AEGIS_DUMMY_SENSOR_EVENT_MAX_SECONDS"] = "0"
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(5))

            sensors = [generator.factory_state()["payload"]["sensor"] for _ in range(4)]

            self.assertGreater(sensors[0]["temperature_celsius_avg"], 32.0)
            self.assertGreater(sensors[1]["humidity_percent_avg"], 70.0)
            self.assertGreater(sensors[2]["pressure_hpa_avg"], 1030.0)
            self.assertLess(sensors[3]["pressure_hpa_avg"], 990.0)

    def test_infra_round_robin_can_emit_warning_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            os.environ["AEGIS_DUMMY_INFRA_EVENT_MIN_SECONDS"] = "0"
            os.environ["AEGIS_DUMMY_INFRA_EVENT_MAX_SECONDS"] = "0"
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(6))

            storage = generator.infra_state()["payload"]
            device = generator.infra_state()["payload"]
            pods = generator.infra_state()["payload"]
            nodes = generator.infra_state()["payload"]

            self.assertGreater(max(node["disk_usage_percent"] for node in storage["nodes"]), 75.0)
            self.assertTrue(any(info["available"] is False for info in device["devices"].values()))
            self.assertEqual(pods["workload_summary"], {"total": 2, "running": 1, "not_running": 1})
            self.assertEqual(nodes["node_summary"], {"total": 2, "ready": 1, "not_ready": 1})

    def test_pipeline_gap_event_uses_warning_freshness_range(self):
        generator = generator_module.FactoryBDummyGenerator(rng=random.Random(7))

        gap = generator._pipeline_gap_seconds("pipeline_warning_gap")

        self.assertGreaterEqual(gap, 45.0)
        self.assertLessEqual(gap, 55.0)

    def test_write_outbox_is_idempotent_for_same_message_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_SEQUENCE_FILE"] = str(Path(tmp) / "seq")
            generator = generator_module.FactoryBDummyGenerator(rng=random.Random(8))
            message = generator.factory_state()
            outbox = Path(tmp) / "outbox"

            first = generator.write_outbox(message, outbox)
            second = generator.write_outbox(message, outbox)

            self.assertEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue((outbox / "tmp").is_dir())


if __name__ == "__main__":
    unittest.main()
