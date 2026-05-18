import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "edge_iot_publisher.py"
SPEC = importlib.util.spec_from_file_location("edge_iot_publisher", MODULE_PATH)
publisher_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(publisher_module)


def sample_message(message_id="factory-a:factory_state:worker2:2026-05-18T01:00:00Z"):
    return {
        "schema_version": "0.1.0",
        "message_id": message_id,
        "factory_id": "factory-a",
        "node_id": "worker2",
        "environment_type": "physical-rpi",
        "input_module_type": "sensor",
        "source_type": "factory_state",
        "source_timestamp": "2026-05-18T01:00:00Z",
        "published_at": "2026-05-18T01:00:00Z",
        "data_plane_instance_id": "adapter",
        "payload": {"sensor": {"sample_count": 1}},
    }


class FakeMqttClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.published = []

    def publish(self, topic, payload):
        if self.fail:
            raise RuntimeError("publish failed")
        self.published.append((topic, json.loads(payload.decode("utf-8"))))


class EdgeIotPublisherTest(unittest.TestCase):
    def setUp(self):
        self.old_env = os.environ.copy()
        os.environ["AEGIS_DATA_PLANE_INSTANCE_ID"] = "publisher-test"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_publish_file_sends_topic_updates_publish_fields_and_deletes_file(self):
        mqtt = FakeMqttClient()
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox)
            path = outbox / "message.json"
            path.write_text(json.dumps(sample_message()), encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)
            with redirect_stdout(io.StringIO()):
                publisher.publish_file(path)

            self.assertFalse(path.exists())
            self.assertEqual(mqtt.published[0][0], "aegis/factory-a/factory_state")
            published_message = mqtt.published[0][1]
            self.assertEqual(published_message["data_plane_instance_id"], "publisher-test")
            self.assertNotEqual(published_message["published_at"], "2026-05-18T01:00:00Z")

    def test_publish_failure_keeps_file_for_retry(self):
        mqtt = FakeMqttClient(fail=True)
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox)
            path = outbox / "message.json"
            path.write_text(json.dumps(sample_message()), encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)

            with self.assertRaises(RuntimeError):
                publisher.publish_file(path)
            self.assertTrue(path.exists())

    def test_invalid_file_moves_to_quarantine(self):
        mqtt = FakeMqttClient()
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox)
            path = outbox / "bad.json"
            path.write_text("{", encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)

            with self.assertRaises(json.JSONDecodeError):
                publisher.publish_file(path)
            self.assertFalse(path.exists())
            self.assertTrue((outbox / "quarantine" / "bad.json").exists())

    def test_scan_outbox_ignores_nested_directories(self):
        mqtt = FakeMqttClient()
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox)
            first = outbox / "a.json"
            nested = outbox / "tmp"
            nested.mkdir()
            first.write_text(json.dumps(sample_message()), encoding="utf-8")
            (nested / "b.json").write_text(json.dumps(sample_message("nested")), encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)

            self.assertEqual(publisher.scan_outbox(), [first])


if __name__ == "__main__":
    unittest.main()
