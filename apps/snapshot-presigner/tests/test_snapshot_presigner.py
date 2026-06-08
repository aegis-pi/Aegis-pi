import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


class FakeS3:
    def __init__(self):
        self.calls = []

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn, HttpMethod):
        self.calls.append(
            {
                "ClientMethod": ClientMethod,
                "Params": Params,
                "ExpiresIn": ExpiresIn,
                "HttpMethod": HttpMethod,
            }
        )
        return "https://upload.example/presigned"


fake_s3 = FakeS3()
sys.modules["boto3"] = SimpleNamespace(client=lambda service: fake_s3)

MODULE_PATH = Path(__file__).resolve().parents[1] / "lambda_function.py"
SPEC = importlib.util.spec_from_file_location("snapshot_presigner", MODULE_PATH)
presigner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(presigner)


def request_body(**overrides):
    payload = {
        "factory_id": "factory-a",
        "node_id": "worker2",
        "filename": "260608094235_event_FALLEN.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 60345,
        "sha256": "a" * 64,
        "source_timestamp": "2026-06-08T09:42:35Z",
        "event_type": "FALLEN",
    }
    payload.update(overrides)
    return payload


def event(payload, headers=None):
    return {
        "headers": headers or {},
        "body": json.dumps(payload),
        "requestContext": {"http": {"method": "POST"}},
    }


class SnapshotPresignerTest(unittest.TestCase):
    def setUp(self):
        self.old_env = os.environ.copy()
        os.environ["S3_BUCKET_NAME"] = "aegis-bucket-data"
        os.environ["ALLOWED_FACTORY_IDS"] = "factory-a"
        os.environ["MAX_FILE_BYTES"] = "5242880"
        os.environ["PRESIGN_EXPIRES_IN_SECONDS"] = "300"
        os.environ.pop("PRESIGN_SHARED_TOKEN", None)
        fake_s3.calls.clear()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_returns_presigned_put_for_valid_request(self):
        response = presigner.handler(event(request_body()), None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["method"], "PUT")
        self.assertEqual(body["upload_url"], "https://upload.example/presigned")
        self.assertEqual(body["expires_in"], 300)
        self.assertEqual(body["s3_bucket"], "aegis-bucket-data")
        self.assertEqual(
            body["s3_key"],
            "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
        )
        self.assertEqual(body["required_headers"], {"Content-Type": "image/jpeg"})
        self.assertEqual(fake_s3.calls[0]["ClientMethod"], "put_object")
        self.assertEqual(fake_s3.calls[0]["Params"]["ContentType"], "image/jpeg")

    def test_rejects_disallowed_factory(self):
        response = presigner.handler(event(request_body(factory_id="factory-b")), None)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("factory_id is not allowed", json.loads(response["body"])["error"])
        self.assertEqual(fake_s3.calls, [])

    def test_rejects_path_filename(self):
        response = presigner.handler(event(request_body(filename="../bad.jpg")), None)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("filename", json.loads(response["body"])["error"])
        self.assertEqual(fake_s3.calls, [])

    def test_rejects_dotdot_filename_without_path_separator(self):
        response = presigner.handler(event(request_body(filename="..bad.jpg")), None)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("filename", json.loads(response["body"])["error"])
        self.assertEqual(fake_s3.calls, [])

    def test_rejects_unsupported_content_type(self):
        response = presigner.handler(event(request_body(content_type="image/gif")), None)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("unsupported content_type", json.loads(response["body"])["error"])

    def test_rejects_oversized_file(self):
        response = presigner.handler(event(request_body(size_bytes=5242881)), None)

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("size_bytes", json.loads(response["body"])["error"])

    def test_requires_bearer_token_when_configured(self):
        os.environ["PRESIGN_SHARED_TOKEN"] = "secret-token"

        unauthorized = presigner.handler(event(request_body()), None)
        authorized = presigner.handler(
            event(request_body(), headers={"Authorization": "Bearer secret-token"}),
            None,
        )

        self.assertEqual(unauthorized["statusCode"], 401)
        self.assertEqual(authorized["statusCode"], 200)


if __name__ == "__main__":
    unittest.main()
