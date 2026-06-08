# Snapshot Uploader

`snapshot-uploader` scans Safe-Edge image snapshots, uploads each image with a presigned S3 PUT URL, and writes only image metadata JSON into the existing AEGIS outbox. The IoT publisher then publishes that metadata to `aegis/{factory_id}/image_snapshot`.

It is a polling uploader, not an inotify-based filesystem trigger. The process scans `AEGIS_SNAPSHOT_DIR` every `AEGIS_SCAN_INTERVAL_SECONDS` seconds and compares each candidate file with local upload state. Existing files that were present before deployment are uploaded once if they are not already recorded in state.

The original image stays on the worker node. This uploader mounts the snapshot directory read-only and never deletes local files.

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

## Runtime Contract

1. Scan `/var/lib/safe-edge/snapshots` for image files.
2. Parse timestamp and event type from names such as `260608114226_event_FIRE.jpg`.
3. Calculate `sha256`, size, and content type.
4. Call the presigner API.
5. Upload the image bytes to S3 with the returned presigned PUT URL.
6. Write an `image_snapshot` metadata envelope to `/var/lib/aegis/outbox`.

The outbox message is a separate canonical message:

```text
source_type=image_snapshot
topic=aegis/{factory_id}/image_snapshot
```

It is not embedded in `factory_state`.

The local upload state is stored at:

```text
/var/lib/aegis/outbox/.snapshot-uploader-state.json
```

State entries include file path, size, mtime, sha256, uploaded time, and S3 key. If this state file is corrupt, the uploader renames it with a `.bad` suffix and continues. If S3 upload succeeded but state write failed, the uploader can recover state from an existing outbox metadata JSON with matching size and sha256.

## S3 Paths

Original image object:

```text
s3://aegis-bucket-data/image_snapshot/factory_id={factory_id}/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{filename}
```

Raw metadata after IoT Core:

```text
s3://aegis-bucket-data/raw/{factory_id}/image_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
```

Processed metadata after DataProcessor:

```text
s3://aegis-bucket-data/processed/{factory_id}/image_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
```

## Local Run

```bash
AEGIS_PRESIGN_ENDPOINT=https://example.internal/presign \
python3 apps/snapshot-uploader/snapshot_uploader.py --once
```

## Tests

```bash
python3 -m unittest discover -s apps/snapshot-uploader/tests
```
