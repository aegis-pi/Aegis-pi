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


def sample_image_snapshot_message():
    message = sample_message("factory-a:image_snapshot:worker2:2026-06-08T09:42:35Z")
    message.update(
        {
            "input_module_type": "camera",
            "source_type": "image_snapshot",
            "source_timestamp": "2026-06-08T09:42:35Z",
            "payload": {
                "event_type": "FALLEN",
                "content_type": "image/jpeg",
                "size_bytes": 60345,
                "sha256": "a" * 64,
                "s3_bucket": "aegis-bucket-data",
                "s3_key": "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
                "local_path": "/var/lib/safe-edge/snapshots/260608094235_event_FALLEN.jpg",
                "upload_status": "uploaded",
            },
        }
    )
    return message


class FakeMqttClient:
    def __init__(self, fail=False, ack_fail=False):
        self.fail = fail
        self.ack_fail = ack_fail
        self.published = []
        self.connected = False
        self.disconnected = False
        self.connect_count = 0

    def publish(self, topic, payload):
        if self.fail:
            raise RuntimeError("publish failed")
        if self.ack_fail:
            raise TimeoutError("publish ack timed out")
        self.published.append((topic, json.loads(payload.decode("utf-8"))))

    def connect(self):
        self.connect_count += 1
        self.connected = True

    def disconnect(self):
        self.disconnected = True


class FakePublishInfo:
    def __init__(self, rc=0, published=True):
        self.rc = rc
        self._published = published
        self.wait_called = False

    def wait_for_publish(self, timeout=None):
        self.wait_called = True

    def is_published(self):
        return self._published


class FakeUnderlyingPahoClient:
    def __init__(self, info=None):
        self.info = info or FakePublishInfo()
        self.connected = False
        self.connect_count = 0
        self.loop_started = False
        self.loop_stopped = False
        self.disconnected = False
        self.published = []
        self.on_connect = None

    def is_connected(self):
        return self.connected

    def connect(self, endpoint, port, keepalive):
        self.connect_count += 1
        self.connected = True
        if self.on_connect:
            self.on_connect(self, None, None, 0)

    def loop_start(self):
        self.loop_started = True

    def publish(self, topic, payload=None, qos=0):
        self.published.append((topic, payload, qos))
        return self.info

    def disconnect(self):
        self.disconnected = True
        self.connected = False

    def loop_stop(self):
        self.loop_stopped = True


class FakeMqttModule:
    MQTT_ERR_SUCCESS = 0


class ConnectFailsOnceMqttClient(FakeMqttClient):
    def __init__(self):
        super().__init__()
        self.after_second_connect = None

    def connect(self):
        self.connect_count += 1
        if self.connect_count == 1:
            raise RuntimeError("connect failed")
        self.connected = True
        if self.after_second_connect:
            self.after_second_connect()


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

    def test_publish_ack_failure_keeps_file_for_retry(self):
        mqtt = FakeMqttClient(ack_fail=True)
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox)
            path = outbox / "message.json"
            path.write_text(json.dumps(sample_message()), encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)

            with self.assertRaises(TimeoutError):
                publisher.publish_file(path)
            self.assertTrue(path.exists())

    def test_publish_once_retries_file_after_previous_publish_failure(self):
        mqtt = FakeMqttClient(fail=True)
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox)
            path = outbox / "message.json"
            path.write_text(json.dumps(sample_message()), encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)

            with redirect_stdout(io.StringIO()):
                self.assertEqual(publisher.publish_once(), 0)
            self.assertTrue(path.exists())

            mqtt.fail = False
            with redirect_stdout(io.StringIO()):
                self.assertEqual(publisher.publish_once(), 1)
            self.assertFalse(path.exists())

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
            (outbox / ".snapshot-uploader-state.json").write_text("{}", encoding="utf-8")
            (nested / "b.json").write_text(json.dumps(sample_message("nested")), encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)

            self.assertEqual(publisher.scan_outbox(), [first])

    def test_image_snapshot_source_type_is_valid_and_uses_image_topic(self):
        mqtt = FakeMqttClient()
        publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)
        message = sample_image_snapshot_message()

        publisher.validate_message(message)

        self.assertEqual(publisher.topic_for(message), "aegis/factory-a/image_snapshot")

    def test_missing_required_image_snapshot_field_moves_to_quarantine(self):
        mqtt = FakeMqttClient()
        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox)
            path = outbox / "image-snapshot.json"
            message = sample_image_snapshot_message()
            del message["source_timestamp"]
            path.write_text(json.dumps(message), encoding="utf-8")

            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)

            with self.assertRaises(ValueError):
                publisher.publish_file(path)
            self.assertFalse(path.exists())
            self.assertTrue((outbox / "quarantine" / "image-snapshot.json").exists())

    def test_run_loop_disconnects_on_graceful_stop(self):
        mqtt = FakeMqttClient()
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_OUTBOX_DIR"] = tmp
            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)
            publisher.stop(15)

            publisher.run_loop()

            self.assertTrue(mqtt.disconnected)

    def test_run_loop_retries_connect_after_connect_failure(self):
        mqtt = ConnectFailsOnceMqttClient()
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AEGIS_OUTBOX_DIR"] = tmp
            os.environ["AEGIS_PUBLISHER_BACKOFF_SECONDS"] = "0.001"
            os.environ["AEGIS_PUBLISHER_MAX_BACKOFF_SECONDS"] = "0.001"
            publisher = publisher_module.EdgeIotPublisher(mqtt_client=mqtt)
            mqtt.after_second_connect = publisher.stop

            publisher.run_loop()

            self.assertEqual(mqtt.connect_count, 2)
            self.assertTrue(mqtt.disconnected)

    def test_paho_client_uses_qos1_and_waits_for_publish_ack(self):
        info = FakePublishInfo()
        fake_client = FakeUnderlyingPahoClient(info=info)
        client = publisher_module.PahoMqttClient(
            endpoint="example.iot",
            port=8883,
            client_id="AEGIS-IoTThing-factory-a",
            ca_file="ca.pem",
            cert_file="cert.pem",
            key_file="key.pem",
        )
        client._mqtt = FakeMqttModule()
        client._client = fake_client
        fake_client.on_connect = client._on_connect

        client.publish("aegis/factory-a/factory_state", b"{}")

        self.assertEqual(fake_client.connect_count, 1)
        self.assertEqual(fake_client.published[0], ("aegis/factory-a/factory_state", b"{}", 1))
        self.assertTrue(info.wait_called)

    def test_paho_client_reconnects_when_underlying_client_is_disconnected(self):
        fake_client = FakeUnderlyingPahoClient()
        client = publisher_module.PahoMqttClient(
            endpoint="example.iot",
            port=8883,
            client_id="AEGIS-IoTThing-factory-a",
            ca_file="ca.pem",
            cert_file="cert.pem",
            key_file="key.pem",
        )
        client._mqtt = FakeMqttModule()
        client._client = fake_client
        fake_client.on_connect = client._on_connect

        client.publish("aegis/factory-a/factory_state", b"{}")
        fake_client.connected = False
        client.publish("aegis/factory-a/factory_state", b"{}")

        self.assertEqual(fake_client.connect_count, 2)


if __name__ == "__main__":
    unittest.main()
