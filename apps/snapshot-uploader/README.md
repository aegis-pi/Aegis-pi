# Snapshot Uploader

`snapshot-uploader` scans Safe-Edge image snapshots, uploads each image with a presigned S3 PUT URL, and writes only image metadata JSON into the existing AEGIS outbox. The IoT publisher then publishes that metadata to `aegis/{factory_id}/image_snapshot`.

## Configuration

| Environment variable | Default |
| --- | --- |
| `AEGIS_FACTORY_ID` | `factory-a` |
| `AEGIS_ENVIRONMENT_TYPE` | `physical-rpi` |
| `AEGIS_INPUT_MODULE_TYPE` | `camera` |
| `AEGIS_SNAPSHOT_DIR` | `/var/lib/safe-edge/snapshots` |
| `AEGIS_OUTBOX_DIR` | `/var/lib/aegis/outbox` |
| `AEGIS_PRESIGN_ENDPOINT` | required |
| `AEGIS_PRESIGN_TOKEN` | empty |
| `AEGIS_UPLOAD_STATE_PATH` | `/var/lib/aegis/outbox/.snapshot-uploader-state.json` |
| `AEGIS_SCAN_INTERVAL_SECONDS` | `10` |
| `AEGIS_MAX_FILE_BYTES` | `5242880` |
| `AEGIS_NODE_ID` | hostname |
| `AEGIS_DATA_PLANE_INSTANCE_ID` | `snapshot-uploader-{node_id}` |

The uploader supports `.jpg`, `.jpeg`, and `.png`. It never sends image bytes to IoT Core and does not use long-lived AWS credentials on the edge node.

## Local Run

```bash
AEGIS_PRESIGN_ENDPOINT=https://example.internal/presign \
python3 apps/snapshot-uploader/snapshot_uploader.py --once
```

## Tests

```bash
python3 -m unittest discover -s apps/snapshot-uploader/tests
```
