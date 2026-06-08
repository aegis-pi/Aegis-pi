import base64
import json
import os
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any

import boto3


CONTENT_TYPES = {"image/jpeg", "image/png"}
DEFAULT_MAX_FILE_BYTES = 5 * 1024 * 1024

_s3 = boto3.client("s3")


def handler(event, context):
    if event and event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _response(204, {})

    auth_result = _authorize(event or {})
    if auth_result is not None:
        return auth_result

    try:
        payload = _json_body(event or {})
        request = _validate(payload)
        s3_bucket = os.environ.get("S3_BUCKET_NAME", "aegis-bucket-data")
        expires_in = int(os.environ.get("PRESIGN_EXPIRES_IN_SECONDS", "300"))
        s3_key = _s3_key(request["factory_id"], request["source_timestamp"], request["filename"])
        upload_url = _s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": s3_bucket,
                "Key": s3_key,
                "ContentType": request["content_type"],
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
    except ValueError as exc:
        return _response(400, {"error": str(exc)})

    return _response(
        200,
        {
            "method": "PUT",
            "upload_url": upload_url,
            "expires_in": expires_in,
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "required_headers": {
                "Content-Type": request["content_type"],
            },
        },
    )


def _authorize(event: dict[str, Any]):
    expected = os.environ.get("PRESIGN_SHARED_TOKEN", "")
    if not expected:
        return None

    headers = {str(k).lower(): str(v) for k, v in (event.get("headers") or {}).items()}
    authorization = headers.get("authorization", "")
    if authorization != f"Bearer {expected}":
        return _response(401, {"error": "unauthorized"})
    return None


def _json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if not body:
        raise ValueError("request body is required")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def _validate(payload: dict[str, Any]) -> dict[str, Any]:
    required = [
        "factory_id",
        "node_id",
        "filename",
        "content_type",
        "size_bytes",
        "sha256",
        "source_timestamp",
        "event_type",
    ]
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    factory_id = _text(payload["factory_id"], "factory_id")
    allowed_factories = _allowed_factories()
    if factory_id not in allowed_factories:
        raise ValueError(f"factory_id is not allowed: {factory_id}")

    filename = _text(payload["filename"], "filename")
    if not _safe_basename(filename):
        raise ValueError("filename must be a safe basename")

    content_type = _text(payload["content_type"], "content_type")
    if content_type not in CONTENT_TYPES:
        raise ValueError(f"unsupported content_type: {content_type}")

    try:
        size_bytes = int(payload["size_bytes"])
    except (TypeError, ValueError) as exc:
        raise ValueError("size_bytes must be an integer") from exc
    max_file_bytes = int(os.environ.get("MAX_FILE_BYTES", str(DEFAULT_MAX_FILE_BYTES)))
    if size_bytes <= 0 or size_bytes > max_file_bytes:
        raise ValueError(f"size_bytes must be between 1 and {max_file_bytes}")

    sha256 = _text(payload["sha256"], "sha256")
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256.lower()):
        raise ValueError("sha256 must be a 64-character hex string")

    source_timestamp = _parse_timestamp(_text(payload["source_timestamp"], "source_timestamp"))

    return {
        "factory_id": factory_id,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "sha256": sha256.lower(),
        "source_timestamp": source_timestamp,
        "event_type": _text(payload["event_type"], "event_type"),
        "node_id": _text(payload["node_id"], "node_id"),
    }


def _allowed_factories() -> set[str]:
    return {
        item.strip()
        for item in os.environ.get("ALLOWED_FACTORY_IDS", "factory-a").split(",")
        if item.strip()
    }


def _safe_basename(filename: str) -> bool:
    if filename in {"", ".", ".."}:
        return False
    if "/" in filename or "\\" in filename:
        return False
    if PurePath(filename).name != filename:
        return False
    return ".." not in filename


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("source_timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("source_timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _s3_key(factory_id: str, source_timestamp: datetime, filename: str) -> str:
    return (
        f"image_snapshot/factory_id={factory_id}/"
        f"yyyy={source_timestamp:%Y}/mm={source_timestamp:%m}/dd={source_timestamp:%d}/"
        f"hh={source_timestamp:%H}/{filename}"
    )


def _text(value: Any, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _response(status_code: int, body: dict[str, Any]):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body, separators=(",", ":"), sort_keys=True),
    }
