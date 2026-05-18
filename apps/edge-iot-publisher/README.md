# Edge IoT Publisher

`edge-iot-publisher` reads canonical AEGIS JSON files from the local spool/outbox and publishes them to AWS IoT Core. It does not collect sensor data directly.

## Configuration

| Environment variable | Default |
| --- | --- |
| `AEGIS_OUTBOX_DIR` | `/var/lib/aegis/outbox` |
| `AEGIS_DATA_PLANE_INSTANCE_ID` | `edge-iot-publisher-{hostname}` |
| `AEGIS_IOT_ENDPOINT` | required |
| `AEGIS_IOT_PORT` | `8883` |
| `AEGIS_IOT_CLIENT_ID` | `AEGIS_DATA_PLANE_INSTANCE_ID` |
| `AEGIS_IOT_CA_FILE` | required |
| `AEGIS_IOT_CERT_FILE` | required |
| `AEGIS_IOT_KEY_FILE` | required |
| `AEGIS_IOT_TIMEOUT_SECONDS` | `10` |
| `AEGIS_PUBLISHER_BACKOFF_SECONDS` | `5` |
| `AEGIS_PUBLISHER_MAX_BACKOFF_SECONDS` | `60` |

## Behavior

The publisher scans only `*.json` files directly under the outbox root. It ignores `tmp/` and `quarantine/` directories.

For every valid message it:

1. overwrites `published_at` with the actual publish time,
2. overwrites `data_plane_instance_id` with the publisher instance ID,
3. publishes to `aegis/{factory_id}/{source_type}`,
4. deletes the local outbox file after successful publish.

Invalid JSON or schema-invalid files are moved to `outbox/quarantine/`. Publish failures leave the file in the outbox for retry.

## Local Run

```bash
AEGIS_IOT_ENDPOINT=example-ats.iot.ap-northeast-2.amazonaws.com \
AEGIS_IOT_CA_FILE=/etc/aegis/iot/AmazonRootCA1.pem \
AEGIS_IOT_CERT_FILE=/etc/aegis/iot/device.pem.crt \
AEGIS_IOT_KEY_FILE=/etc/aegis/iot/private.pem.key \
python3 apps/edge-iot-publisher/edge_iot_publisher.py --once
```

Run continuously:

```bash
python3 apps/edge-iot-publisher/edge_iot_publisher.py --loop
```

## Tests

```bash
python3 -m unittest discover -s apps/edge-iot-publisher/tests
```
