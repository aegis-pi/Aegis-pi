import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "snapshot_uploader.py"
SPEC = importlib.util.spec_from_file_location("snapshot_uploader", MODULE_PATH)
uploader_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["snapshot_uploader"] = uploader_module
SPEC.loader.exec_module(uploader_module)


class FakePresignClient:
    def __init__(self):
        self.requests = []

    def request_upload(self, payload):
        self.requests.append(payload)
        timestamp = datetime.fromisoformat(payload["source_timestamp"].replace("Z", "+00:00"))
        return {
            "method": "PUT",
            "upload_url": "https://upload.example/object",
            "expires_in": 300,
            "s3_bucket": "aegis-bucket-data",
            "s3_key": uploader_module.s3_key_for(payload["factory_id"], timestamp, payload["filename"]),
            "required_headers": {"Content-Type": payload["content_type"]},
        }


class FakePutClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.puts = []

    def put_file(self, upload_url, path, headers):
        if self.fail:
            raise RuntimeError("put failed")
        self.puts.append((upload_url, path.read_bytes(), headers))


class SnapshotUploaderTest(unittest.TestCase):
    def setUp(self):
        self.old_env = os.environ.copy()
        os.environ["AEGIS_FACTORY_ID"] = "factory-a"
        os.environ["AEGIS_NODE_ID"] = "worker2"
        os.environ["AEGIS_DATA_PLANE_INSTANCE_ID"] = "snapshot-uploader-worker2"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_parse_filename_timestamp_event_type_and_s3_key(self):
        path = Path("/var/lib/safe-edge/snapshots/260608094235_event_FALLEN.jpg")
        timestamp = uploader_module.parse_snapshot_timestamp(path)

        self.assertEqual(uploader_module.format_utc(timestamp), "2026-06-08T09:42:35Z")
        self.assertEqual(uploader_module.parse_event_type(path), "FALLEN")
        self.assertEqual(
            uploader_module.s3_key_for("factory-a", timestamp, path.name),
            "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
        )

    def test_scan_skips_unsupported_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_dir = Path(tmp)
            (snapshot_dir / "a.jpg").write_bytes(b"jpg")
            (snapshot_dir / "b.png").write_bytes(b"png")
            (snapshot_dir / "c.txt").write_text("ignore", encoding="utf-8")
            os.environ["AEGIS_SNAPSHOT_DIR"] = str(snapshot_dir)

            uploader = uploader_module.SnapshotUploader(FakePresignClient(), FakePutClient())

            self.assertEqual([item.name for item in uploader.scan_snapshots()], ["a.jpg", "b.png"])

    def test_process_once_uploads_and_writes_metadata_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot_dir = root / "snapshots"
            outbox_dir = root / "outbox"
            snapshot_dir.mkdir()
            image = snapshot_dir / "260608094235_event_FALLEN.jpg"
            image.write_bytes(b"image-bytes")
            os.environ["AEGIS_SNAPSHOT_DIR"] = str(snapshot_dir)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox_dir)
            os.environ["AEGIS_UPLOAD_STATE_PATH"] = str(outbox_dir / ".snapshot-uploader-state.json")

            presign = FakePresignClient()
            put = FakePutClient()
            uploader = uploader_module.SnapshotUploader(presign, put)

            uploaded = uploader.process_once()

            self.assertEqual(uploaded, 1)
            self.assertEqual(len(presign.requests), 1)
            self.assertEqual(presign.requests[0]["filename"], "260608094235_event_FALLEN.jpg")
            self.assertEqual(presign.requests[0]["content_type"], "image/jpeg")
            self.assertEqual(presign.requests[0]["source_timestamp"], "2026-06-08T09:42:35Z")
            self.assertEqual(len(put.puts), 1)
            metadata_path = outbox_dir / "factory-a:image_snapshot:worker2:2026-06-08T09:42:35Z.json"
            self.assertTrue(metadata_path.exists())
            message = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(message["source_type"], "image_snapshot")
            self.assertIsNone(message["published_at"])
            self.assertEqual(message["payload"]["upload_status"], "uploaded")
            self.assertEqual(message["payload"]["s3_bucket"], "aegis-bucket-data")
            self.assertEqual(
                message["payload"]["s3_key"],
                "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
            )
            self.assertTrue((outbox_dir / "tmp").is_dir())
            self.assertTrue((outbox_dir / ".snapshot-uploader-state.json").exists())

    def test_state_skip_avoids_reupload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot_dir = root / "snapshots"
            outbox_dir = root / "outbox"
            snapshot_dir.mkdir()
            image = snapshot_dir / "260608094235_event_FALLEN.jpg"
            image.write_bytes(b"image-bytes")
            os.environ["AEGIS_SNAPSHOT_DIR"] = str(snapshot_dir)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox_dir)
            os.environ["AEGIS_UPLOAD_STATE_PATH"] = str(outbox_dir / ".snapshot-uploader-state.json")

            presign = FakePresignClient()
            uploader = uploader_module.SnapshotUploader(presign, FakePutClient())

            self.assertEqual(uploader.process_once(), 1)
            self.assertEqual(uploader.process_once(), 0)
            self.assertEqual(len(presign.requests), 1)

    def test_oversized_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_dir = Path(tmp) / "snapshots"
            snapshot_dir.mkdir()
            image = snapshot_dir / "260608094235_event_FALLEN.jpg"
            image.write_bytes(b"too-large")
            os.environ["AEGIS_SNAPSHOT_DIR"] = str(snapshot_dir)
            os.environ["AEGIS_MAX_FILE_BYTES"] = "1"

            uploader = uploader_module.SnapshotUploader(FakePresignClient(), FakePutClient())

            self.assertIsNone(uploader.candidate_for(image))

    def test_put_failure_does_not_write_metadata_or_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot_dir = root / "snapshots"
            outbox_dir = root / "outbox"
            snapshot_dir.mkdir()
            image = snapshot_dir / "260608094235_event_FALLEN.jpg"
            image.write_bytes(b"image-bytes")
            os.environ["AEGIS_SNAPSHOT_DIR"] = str(snapshot_dir)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox_dir)
            os.environ["AEGIS_UPLOAD_STATE_PATH"] = str(outbox_dir / ".snapshot-uploader-state.json")

            uploader = uploader_module.SnapshotUploader(FakePresignClient(), FakePutClient(fail=True))

            self.assertEqual(uploader.process_once(), 0)
            self.assertFalse((outbox_dir / "factory-a:image_snapshot:worker2:2026-06-08T09:42:35Z.json").exists())
            self.assertFalse((outbox_dir / ".snapshot-uploader-state.json").exists())

    def test_corrupt_state_is_quarantined_and_upload_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot_dir = root / "snapshots"
            outbox_dir = root / "outbox"
            snapshot_dir.mkdir()
            outbox_dir.mkdir()
            image = snapshot_dir / "260608094235_event_FALLEN.jpg"
            image.write_bytes(b"image-bytes")
            state_path = outbox_dir / ".snapshot-uploader-state.json"
            state_path.write_text("{", encoding="utf-8")
            os.environ["AEGIS_SNAPSHOT_DIR"] = str(snapshot_dir)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox_dir)
            os.environ["AEGIS_UPLOAD_STATE_PATH"] = str(state_path)

            uploader = uploader_module.SnapshotUploader(FakePresignClient(), FakePutClient())

            self.assertEqual(uploader.process_once(), 1)
            self.assertTrue((outbox_dir / ".snapshot-uploader-state.json").exists())
            self.assertEqual(len(list(outbox_dir.glob(".snapshot-uploader-state.json.*.bad"))), 1)

    def test_existing_outbox_metadata_recovers_state_without_reupload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot_dir = root / "snapshots"
            outbox_dir = root / "outbox"
            snapshot_dir.mkdir()
            outbox_dir.mkdir()
            image = snapshot_dir / "260608094235_event_FALLEN.jpg"
            image.write_bytes(b"image-bytes")
            os.environ["AEGIS_SNAPSHOT_DIR"] = str(snapshot_dir)
            os.environ["AEGIS_OUTBOX_DIR"] = str(outbox_dir)
            os.environ["AEGIS_UPLOAD_STATE_PATH"] = str(outbox_dir / ".snapshot-uploader-state.json")

            uploader = uploader_module.SnapshotUploader(FakePresignClient(), FakePutClient())
            candidate = uploader.candidate_for(image)
            message = uploader.metadata_message(
                candidate,
                "aegis-bucket-data",
                "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
            )
            metadata_path = outbox_dir / "factory-a:image_snapshot:worker2:2026-06-08T09:42:35Z.json"
            metadata_path.write_text(json.dumps(message), encoding="utf-8")

            presign = FakePresignClient()
            put = FakePutClient()
            uploader = uploader_module.SnapshotUploader(presign, put)

            self.assertEqual(uploader.process_once(), 0)
            self.assertEqual(presign.requests, [])
            self.assertEqual(put.puts, [])
            state = json.loads((outbox_dir / ".snapshot-uploader-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state[str(image)]["sha256"], candidate.sha256)

    def test_run_loop_catches_process_once_errors(self):
        uploader = uploader_module.SnapshotUploader(FakePresignClient(), FakePutClient())
        calls = []

        def process_once():
            calls.append("process")
            raise RuntimeError("boom")

        def sleep(seconds):
            raise KeyboardInterrupt()

        uploader.process_once = process_once
        old_sleep = uploader_module.time.sleep
        uploader_module.time.sleep = sleep
        try:
            with self.assertRaises(KeyboardInterrupt):
                uploader.run_loop()
        finally:
            uploader_module.time.sleep = old_sleep

        self.assertEqual(calls, ["process"])


if __name__ == "__main__":
    unittest.main()
