#!/usr/bin/env python3
"""Upload Safe-Edge image snapshots to S3 and spool metadata to AEGIS outbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
DEFAULT_MAX_FILE_BYTES = 5 * 1024 * 1024


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_snapshot_timestamp(path: Path) -> datetime | None:
    prefix = path.stem.split("_", 1)[0]
    if len(prefix) != 12 or not prefix.isdigit():
        return None
    try:
        return datetime.strptime(prefix, "%y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def source_timestamp_for(path: Path) -> datetime:
    return parse_snapshot_timestamp(path) or datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def parse_event_type(path: Path) -> str:
    parts = path.stem.split("_")
    if "event" in parts:
        index = parts.index("event")
        if index + 1 < len(parts):
            value = "_".join(parts[index + 1 :]).strip()
            if value:
                return value.upper()
    return "UNKNOWN"


def content_type_for(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in SUPPORTED_CONTENT_TYPES:
        return SUPPORTED_CONTENT_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed if guessed in {"image/jpeg", "image/png"} else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def s3_key_for(factory_id: str, source_timestamp: datetime, filename: str) -> str:
    timestamp = source_timestamp.astimezone(timezone.utc)
    return (
        f"image_snapshot/factory_id={factory_id}/"
        f"yyyy={timestamp:%Y}/mm={timestamp:%m}/dd={timestamp:%d}/hh={timestamp:%H}/"
        f"{filename}"
    )


def safe_message_filename(message_id: str) -> str:
    return f"{message_id}.json"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = path.parent / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=tmp_dir,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        tmp_path = Path(handle.name)

    tmp_path.replace(path)
    path.chmod(0o640)
    return path


@dataclass(frozen=True)
class SnapshotCandidate:
    path: Path
    source_timestamp: datetime
    event_type: str
    content_type: str
    size_bytes: int
    mtime_ns: int
    sha256: str


class PresignClient:
    def __init__(self, endpoint: str, timeout_seconds: float = 10.0, token: str = "") -> None:
        if not endpoint:
            raise RuntimeError("AEGIS_PRESIGN_ENDPOINT is required")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.token = token

    def request_upload(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class PutClient:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def put_file(self, upload_url: str, path: Path, headers: dict[str, str]) -> None:
        data = path.read_bytes()
        request_headers = dict(headers)
        request_headers.setdefault("Content-Length", str(len(data)))
        request = urllib.request.Request(upload_url, data=data, headers=request_headers, method="PUT")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            status = getattr(response, "status", response.getcode())
            if status < 200 or status >= 300:
                raise RuntimeError(f"S3 PUT failed with HTTP {status}")


class SnapshotUploader:
    def __init__(self, presign_client: Any | None = None, put_client: Any | None = None) -> None:
        self.factory_id = os.getenv("AEGIS_FACTORY_ID", "factory-a")
        self.environment_type = os.getenv("AEGIS_ENVIRONMENT_TYPE", "physical-rpi")
        self.input_module_type = os.getenv("AEGIS_INPUT_MODULE_TYPE", "camera")
        self.snapshot_dir = Path(os.getenv("AEGIS_SNAPSHOT_DIR", "/var/lib/safe-edge/snapshots"))
        self.outbox_dir = Path(os.getenv("AEGIS_OUTBOX_DIR", "/var/lib/aegis/outbox"))
        self.state_path = Path(os.getenv("AEGIS_UPLOAD_STATE_PATH", "/var/lib/aegis/outbox/.snapshot-uploader-state.json"))
        self.scan_interval_seconds = float(os.getenv("AEGIS_SCAN_INTERVAL_SECONDS", "10"))
        self.max_file_bytes = int(os.getenv("AEGIS_MAX_FILE_BYTES", str(DEFAULT_MAX_FILE_BYTES)))
        self.node_id = os.getenv("AEGIS_NODE_ID", socket.gethostname())
        self.data_plane_instance_id = os.getenv("AEGIS_DATA_PLANE_INSTANCE_ID", f"snapshot-uploader-{self.node_id}")
        timeout_seconds = float(os.getenv("AEGIS_HTTP_TIMEOUT_SECONDS", "10"))
        self.presign_client = presign_client or PresignClient(
            os.getenv("AEGIS_PRESIGN_ENDPOINT", ""),
            timeout_seconds,
            os.getenv("AEGIS_PRESIGN_TOKEN", ""),
        )
        self.put_client = put_client or PutClient(float(os.getenv("AEGIS_PUT_TIMEOUT_SECONDS", "30")))

    def scan_snapshots(self) -> list[Path]:
        if not self.snapshot_dir.exists():
            return []
        candidates: list[tuple[float, str, Path]] = []
        for item in self.snapshot_dir.iterdir():
            try:
                if item.is_file() and item.suffix.lower() in SUPPORTED_CONTENT_TYPES:
                    candidates.append((item.stat().st_mtime, item.name, item))
            except OSError as exc:
                print(f"skip unreadable snapshot path {item}: {exc}", file=sys.stderr, flush=True)
        return [item for _, _, item in sorted(candidates)]

    def load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"failed to read upload state {self.state_path}: {exc}", file=sys.stderr, flush=True)
            self._quarantine_state()
            return {}
        if not isinstance(state, dict):
            print(f"failed to read upload state {self.state_path}: state must be an object", file=sys.stderr, flush=True)
            self._quarantine_state()
            return {}
        return state

    def write_state(self, state: dict[str, Any]) -> None:
        atomic_write_json(self.state_path, state)

    def _quarantine_state(self) -> None:
        try:
            if self.state_path.exists():
                target = self.state_path.with_name(f"{self.state_path.name}.{int(time.time())}.bad")
                self.state_path.replace(target)
        except OSError as exc:
            print(f"failed to quarantine upload state {self.state_path}: {exc}", file=sys.stderr, flush=True)

    def should_skip(self, path: Path, stat_result: os.stat_result, state: dict[str, Any]) -> bool:
        marker = state.get(str(path))
        if not isinstance(marker, dict):
            return False
        return marker.get("size_bytes") == stat_result.st_size and marker.get("mtime_ns") == stat_result.st_mtime_ns

    def candidate_for(self, path: Path) -> SnapshotCandidate | None:
        stat_result = path.stat()
        if stat_result.st_size > self.max_file_bytes:
            print(f"skip oversized snapshot {path}: {stat_result.st_size} bytes", file=sys.stderr, flush=True)
            return None

        content_type = content_type_for(path)
        if content_type is None:
            print(f"skip unsupported snapshot type {path}", file=sys.stderr, flush=True)
            return None

        return SnapshotCandidate(
            path=path,
            source_timestamp=source_timestamp_for(path),
            event_type=parse_event_type(path),
            content_type=content_type,
            size_bytes=stat_result.st_size,
            mtime_ns=stat_result.st_mtime_ns,
            sha256=sha256_file(path),
        )

    def presign_payload(self, candidate: SnapshotCandidate) -> dict[str, Any]:
        return {
            "factory_id": self.factory_id,
            "node_id": self.node_id,
            "filename": candidate.path.name,
            "content_type": candidate.content_type,
            "size_bytes": candidate.size_bytes,
            "sha256": candidate.sha256,
            "source_timestamp": format_utc(candidate.source_timestamp),
            "event_type": candidate.event_type,
        }

    def upload_candidate(self, candidate: SnapshotCandidate) -> dict[str, str]:
        response = self.presign_client.request_upload(self.presign_payload(candidate))
        method = response.get("method", "PUT")
        if method != "PUT":
            raise RuntimeError(f"unsupported presigned upload method: {method}")

        upload_url = response.get("upload_url")
        s3_bucket = response.get("s3_bucket")
        s3_key = response.get("s3_key")
        if not upload_url or not s3_bucket or not s3_key:
            raise RuntimeError("presign response is missing upload_url, s3_bucket, or s3_key")

        headers = {str(k): str(v) for k, v in response.get("required_headers", {}).items()}
        headers.setdefault("Content-Type", candidate.content_type)
        self.put_client.put_file(str(upload_url), candidate.path, headers)
        return {"s3_bucket": str(s3_bucket), "s3_key": str(s3_key)}

    def metadata_message(self, candidate: SnapshotCandidate, s3_bucket: str, s3_key: str) -> dict[str, Any]:
        source_timestamp = format_utc(candidate.source_timestamp)
        message_id = f"{self.factory_id}:image_snapshot:{self.node_id}:{source_timestamp}"
        return {
            "schema_version": "0.1.0",
            "message_id": message_id,
            "factory_id": self.factory_id,
            "node_id": self.node_id,
            "environment_type": self.environment_type,
            "input_module_type": self.input_module_type,
            "source_type": "image_snapshot",
            "source_timestamp": source_timestamp,
            "published_at": None,
            "data_plane_instance_id": self.data_plane_instance_id,
            "payload": {
                "event_type": candidate.event_type,
                "content_type": candidate.content_type,
                "size_bytes": candidate.size_bytes,
                "sha256": candidate.sha256,
                "s3_bucket": s3_bucket,
                "s3_key": s3_key,
                "local_path": str(candidate.path),
                "upload_status": "uploaded",
            },
        }

    def outbox_path_for(self, message: dict[str, Any]) -> Path:
        return self.outbox_dir / safe_message_filename(str(message["message_id"]))

    def recover_state_from_outbox(self, candidate: SnapshotCandidate, state: dict[str, Any]) -> bool:
        source_timestamp = format_utc(candidate.source_timestamp)
        message_id = f"{self.factory_id}:image_snapshot:{self.node_id}:{source_timestamp}"
        path = self.outbox_dir / safe_message_filename(message_id)
        if not path.exists():
            return False
        try:
            message = json.loads(path.read_text(encoding="utf-8"))
            payload = message.get("payload", {})
            if message.get("source_type") != "image_snapshot" or not isinstance(payload, dict):
                return False
            if payload.get("sha256") != candidate.sha256 or payload.get("size_bytes") != candidate.size_bytes:
                return False
            s3_key = payload.get("s3_key")
            if not s3_key:
                return False
            state[str(candidate.path)] = {
                "size_bytes": candidate.size_bytes,
                "mtime_ns": candidate.mtime_ns,
                "sha256": candidate.sha256,
                "s3_key": s3_key,
                "uploaded_at": format_utc(utc_now()),
            }
            self.write_state(state)
            print(f"recovered upload state from existing outbox metadata {path}", flush=True)
            return True
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            print(f"failed to recover upload state from {path}: {exc}", file=sys.stderr, flush=True)
            return False

    def process_once(self) -> int:
        state = self.load_state()
        uploaded = 0
        for path in self.scan_snapshots():
            try:
                stat_result = path.stat()
                if self.should_skip(path, stat_result, state):
                    continue
                candidate = self.candidate_for(path)
                if candidate is None:
                    continue
                if self.recover_state_from_outbox(candidate, state):
                    continue
                upload_result = self.upload_candidate(candidate)
                message = self.metadata_message(candidate, upload_result["s3_bucket"], upload_result["s3_key"])
                atomic_write_json(self.outbox_path_for(message), message)
                state[str(path)] = {
                    "size_bytes": candidate.size_bytes,
                    "mtime_ns": candidate.mtime_ns,
                    "sha256": candidate.sha256,
                    "s3_key": upload_result["s3_key"],
                    "uploaded_at": format_utc(utc_now()),
                }
                self.write_state(state)
                uploaded += 1
                print(f"uploaded {path} -> s3://{upload_result['s3_bucket']}/{upload_result['s3_key']}", flush=True)
            except (OSError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
                print(f"snapshot upload failed for {path}: {exc}", file=sys.stderr, flush=True)
        return uploaded

    def run_loop(self) -> None:
        while True:
            try:
                self.process_once()
            except Exception as exc:
                print(f"snapshot uploader loop error: {exc}", file=sys.stderr, flush=True)
            time.sleep(self.scan_interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Safe-Edge image snapshots to S3.")
    parser.add_argument("--once", action="store_true", help="Scan once and exit.")
    parser.add_argument("--loop", action="store_true", help="Continuously scan and upload.")
    args = parser.parse_args()

    if args.once and args.loop:
        parser.error("--once and --loop are mutually exclusive")

    uploader = SnapshotUploader()
    if args.loop or not args.once:
        uploader.run_loop()
        return 0

    uploader.process_once()
    return 0


if __name__ == "__main__":
    sys.exit(main())
