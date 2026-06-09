#!/usr/bin/env python3
"""Publish AEGIS outbox JSON files to AWS IoT Core."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import ssl
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_SOURCE_TYPES = {"factory_state", "infra_state", "image_snapshot"}
REQUIRED_FIELDS = {
    "schema_version",
    "message_id",
    "factory_id",
    "node_id",
    "environment_type",
    "input_module_type",
    "source_type",
    "source_timestamp",
    "published_at",
    "data_plane_instance_id",
    "payload",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mqtt_remaining_length(length: int) -> bytes:
    encoded = bytearray()
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 0x80
        encoded.append(digit)
        if length == 0:
            return bytes(encoded)


def mqtt_string(value: str) -> bytes:
    payload = value.encode("utf-8")
    if len(payload) > 65535:
        raise ValueError("MQTT string exceeds 65535 bytes")
    return len(payload).to_bytes(2, "big") + payload


def mqtt_connect_packet(client_id: str, keepalive_seconds: int = 60) -> bytes:
    variable_header = mqtt_string("MQTT") + bytes([4, 2]) + keepalive_seconds.to_bytes(2, "big")
    payload = mqtt_string(client_id)
    remaining_length = len(variable_header) + len(payload)
    return bytes([0x10]) + mqtt_remaining_length(remaining_length) + variable_header + payload


def mqtt_publish_packet(topic: str, payload: bytes) -> bytes:
    variable_header = mqtt_string(topic)
    remaining_length = len(variable_header) + len(payload)
    return bytes([0x30]) + mqtt_remaining_length(remaining_length) + variable_header + payload


class RawMqttClient:
    def __init__(
        self,
        *,
        endpoint: str,
        port: int,
        client_id: str,
        ca_file: str,
        cert_file: str,
        key_file: str,
        keepalive_seconds: int = 60,
        timeout_seconds: float = 10.0,
        reconnect_min_delay_seconds: float = 1.0,
        reconnect_max_delay_seconds: float = 60.0,
    ) -> None:
        self.endpoint = endpoint
        self.port = port
        self.client_id = client_id
        self.ca_file = ca_file
        self.cert_file = cert_file
        self.key_file = key_file
        self.keepalive_seconds = keepalive_seconds
        self.timeout_seconds = timeout_seconds

    def publish(self, topic: str, payload: bytes) -> None:
        context = ssl.create_default_context(cafile=self.ca_file)
        context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)

        with socket.create_connection((self.endpoint, self.port), timeout=self.timeout_seconds) as raw_socket:
            with context.wrap_socket(raw_socket, server_hostname=self.endpoint) as tls_socket:
                tls_socket.settimeout(self.timeout_seconds)
                tls_socket.sendall(mqtt_connect_packet(self.client_id, self.keepalive_seconds))
                connack = tls_socket.recv(4)
                if len(connack) != 4 or connack[:3] != b"\x20\x02\x00" or connack[3] != 0:
                    raise RuntimeError(f"MQTT CONNACK rejected: {connack.hex()}")
                tls_socket.sendall(mqtt_publish_packet(topic, payload))
                tls_socket.sendall(b"\xe0\x00")

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None


class PahoMqttClient:
    def __init__(
        self,
        *,
        endpoint: str,
        port: int,
        client_id: str,
        ca_file: str,
        cert_file: str,
        key_file: str,
        keepalive_seconds: int = 60,
        timeout_seconds: float = 10.0,
        reconnect_min_delay_seconds: float = 1.0,
        reconnect_max_delay_seconds: float = 60.0,
    ) -> None:
        self.endpoint = endpoint
        self.port = port
        self.client_id = client_id
        self.ca_file = ca_file
        self.cert_file = cert_file
        self.key_file = key_file
        self.keepalive_seconds = keepalive_seconds
        self.timeout_seconds = timeout_seconds
        self.reconnect_min_delay_seconds = reconnect_min_delay_seconds
        self.reconnect_max_delay_seconds = reconnect_max_delay_seconds
        self._client: Any | None = None
        self._mqtt: Any | None = None
        self._connected = threading.Event()
        self._connect_result = threading.Event()
        self._connect_error: RuntimeError | None = None
        self._loop_started = False

    def connect(self) -> None:
        if self._client is not None and self._client.is_connected():
            return
        if self._client is None:
            self._client = self._build_client()

        self._connected.clear()
        self._connect_result.clear()
        self._connect_error = None
        self._client.connect(self.endpoint, self.port, keepalive=self.keepalive_seconds)
        if not self._loop_started:
            self._client.loop_start()
            self._loop_started = True
        if not self._connect_result.wait(self.timeout_seconds):
            raise TimeoutError(f"MQTT connect timed out for {self.endpoint}:{self.port}")
        if self._connect_error is not None:
            raise self._connect_error

    def publish(self, topic: str, payload: bytes) -> None:
        self.connect()
        info = self._client.publish(topic, payload=payload, qos=1)
        if info.rc != self._mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed before ack: rc={info.rc}")
        info.wait_for_publish(timeout=self.timeout_seconds)
        if not info.is_published():
            raise TimeoutError("MQTT publish ack timed out")

    def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            if self._client.is_connected():
                self._client.disconnect()
        finally:
            if self._loop_started:
                self._client.loop_stop()
                self._loop_started = False
            self._connected.clear()

    def _build_client(self) -> Any:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError("paho-mqtt is required for persistent MQTT publishing") from exc

        self._mqtt = mqtt
        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
                protocol=mqtt.MQTTv311,
            )
        except AttributeError:
            client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)

        client.tls_set(
            ca_certs=self.ca_file,
            certfile=self.cert_file,
            keyfile=self.key_file,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.reconnect_delay_set(
            min_delay=self.reconnect_min_delay_seconds,
            max_delay=self.reconnect_max_delay_seconds,
        )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        return client

    def _on_connect(self, _client: Any, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any = None) -> None:
        if self._reason_code_success(reason_code):
            self._connected.set()
        else:
            self._connect_error = RuntimeError(f"MQTT CONNACK rejected: {reason_code}")
        self._connect_result.set()

    def _on_disconnect(self, *_args: Any) -> None:
        self._connected.clear()

    def _reason_code_success(self, reason_code: Any) -> bool:
        if reason_code == 0:
            return True
        if getattr(reason_code, "value", None) == 0:
            return True
        return str(reason_code).lower() == "success"


class EdgeIotPublisher:
    def __init__(self, mqtt_client: Any | None = None) -> None:
        self.outbox_dir = Path(os.getenv("AEGIS_OUTBOX_DIR", "/var/lib/aegis/outbox"))
        self.data_plane_instance_id = os.getenv(
            "AEGIS_DATA_PLANE_INSTANCE_ID",
            f"edge-iot-publisher-{socket.gethostname()}",
        )
        self.backoff_seconds = float(os.getenv("AEGIS_PUBLISHER_BACKOFF_SECONDS", "5"))
        self.max_backoff_seconds = float(os.getenv("AEGIS_PUBLISHER_MAX_BACKOFF_SECONDS", "60"))
        self.stop_event = threading.Event()
        self.mqtt_client = mqtt_client or self._build_mqtt_client()

    def _build_mqtt_client(self) -> PahoMqttClient | RawMqttClient:
        endpoint = (os.getenv("AEGIS_IOT_ENDPOINT") or "").strip() or None
        ca_file = os.getenv("AEGIS_IOT_CA_FILE")
        cert_file = os.getenv("AEGIS_IOT_CERT_FILE")
        key_file = os.getenv("AEGIS_IOT_KEY_FILE")
        missing = [
            name
            for name, value in (
                ("AEGIS_IOT_ENDPOINT", endpoint),
                ("AEGIS_IOT_CA_FILE", ca_file),
                ("AEGIS_IOT_CERT_FILE", cert_file),
                ("AEGIS_IOT_KEY_FILE", key_file),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"missing required environment variables: {', '.join(missing)}")

        client_class: type[PahoMqttClient] | type[RawMqttClient]
        client_class = RawMqttClient if os.getenv("AEGIS_IOT_MQTT_CLIENT", "paho") == "raw" else PahoMqttClient

        return client_class(
            endpoint=endpoint or "",
            port=int(os.getenv("AEGIS_IOT_PORT", "8883")),
            client_id=os.getenv("AEGIS_IOT_CLIENT_ID", self.data_plane_instance_id),
            ca_file=ca_file or "",
            cert_file=cert_file or "",
            key_file=key_file or "",
            keepalive_seconds=int(os.getenv("AEGIS_IOT_KEEPALIVE_SECONDS", "60")),
            timeout_seconds=float(os.getenv("AEGIS_IOT_TIMEOUT_SECONDS", "10")),
            reconnect_min_delay_seconds=float(os.getenv("AEGIS_IOT_RECONNECT_MIN_DELAY_SECONDS", "1")),
            reconnect_max_delay_seconds=float(os.getenv("AEGIS_IOT_RECONNECT_MAX_DELAY_SECONDS", "60")),
        )

    def scan_outbox(self) -> list[Path]:
        if not self.outbox_dir.exists():
            return []
        return sorted(
            [
                item
                for item in self.outbox_dir.iterdir()
                if item.is_file() and item.suffix == ".json" and not item.name.startswith(".")
            ],
            key=lambda item: (item.stat().st_mtime, item.name),
        )

    def publish_once(self) -> int:
        published = 0
        for path in self.scan_outbox():
            try:
                self.publish_file(path)
            except Exception as exc:
                print(f"publish failed for {path}: {exc}", file=sys.stderr, flush=True)
                continue
            published += 1
        return published

    def run_loop(self) -> None:
        delay = self.backoff_seconds
        try:
            while not self.stop_event.is_set():
                try:
                    if hasattr(self.mqtt_client, "connect"):
                        self.mqtt_client.connect()
                    published = self.publish_once()
                    delay = self.backoff_seconds if published else min(delay * 2, self.max_backoff_seconds)
                except Exception as exc:
                    print(f"publisher loop error: {exc}", file=sys.stderr, flush=True)
                    delay = min(delay * 2, self.max_backoff_seconds)
                self.stop_event.wait(delay)
        finally:
            self.close()

    def publish_file(self, path: Path) -> None:
        try:
            message = json.loads(path.read_text(encoding="utf-8"))
            self.validate_message(message)
        except Exception:
            self.quarantine(path)
            raise

        message["published_at"] = format_utc(utc_now())
        message["data_plane_instance_id"] = self.data_plane_instance_id
        topic = self.topic_for(message)
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.mqtt_client.publish(topic, payload)
        path.unlink()
        print(f"published {path} -> {topic}", flush=True)

    def stop(self, signum: int | None = None, _frame: Any | None = None) -> None:
        if signum is not None:
            print(f"received signal {signum}; stopping publisher", flush=True)
        self.stop_event.set()

    def close(self) -> None:
        if hasattr(self.mqtt_client, "disconnect"):
            self.mqtt_client.disconnect()

    def validate_message(self, message: dict[str, Any]) -> None:
        missing = sorted(REQUIRED_FIELDS - set(message))
        if missing:
            raise ValueError(f"message is missing required fields: {', '.join(missing)}")
        if message.get("source_type") not in VALID_SOURCE_TYPES:
            raise ValueError(f"unsupported source_type: {message.get('source_type')}")
        if not message.get("factory_id"):
            raise ValueError("factory_id is required")
        if not message.get("message_id"):
            raise ValueError("message_id is required")
        if not isinstance(message.get("payload"), dict):
            raise ValueError("payload must be an object")

    def topic_for(self, message: dict[str, Any]) -> str:
        self.validate_message(message)
        return f"aegis/{message['factory_id']}/{message['source_type']}"

    def quarantine(self, path: Path) -> Path:
        target_dir = self.outbox_dir / "quarantine"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / path.name
        if target.exists():
            target = target_dir / f"{path.stem}.{int(time.time())}{path.suffix}"
        path.replace(target)
        return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish AEGIS outbox JSON files to AWS IoT Core.")
    parser.add_argument("--once", action="store_true", help="Scan the outbox once and exit.")
    parser.add_argument("--loop", action="store_true", help="Continuously scan and publish outbox files.")
    parser.add_argument("--outbox-dir", default=os.getenv("AEGIS_OUTBOX_DIR", "/var/lib/aegis/outbox"))
    args = parser.parse_args()

    if args.once and args.loop:
        parser.error("--once and --loop are mutually exclusive")

    os.environ["AEGIS_OUTBOX_DIR"] = args.outbox_dir
    publisher = EdgeIotPublisher()
    signal.signal(signal.SIGTERM, publisher.stop)
    signal.signal(signal.SIGINT, publisher.stop)

    if args.loop or not args.once:
        publisher.run_loop()
        return 0

    try:
        publisher.publish_once()
    finally:
        publisher.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
