FROM python:3.12-slim

WORKDIR /app
COPY snapshot_uploader.py /app/snapshot_uploader.py

ENV AEGIS_FACTORY_ID=factory-a \
    AEGIS_ENVIRONMENT_TYPE=physical-rpi \
    AEGIS_INPUT_MODULE_TYPE=camera \
    AEGIS_SNAPSHOT_DIR=/var/lib/safe-edge/snapshots \
    AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox \
    AEGIS_UPLOAD_STATE_PATH=/var/lib/aegis/outbox/.snapshot-uploader-state.json \
    AEGIS_PRESIGN_TOKEN="" \
    AEGIS_SCAN_INTERVAL_SECONDS=10 \
    AEGIS_MAX_FILE_BYTES=5242880 \
    PYTHONUNBUFFERED=1

USER 1000:1000
ENTRYPOINT ["python3", "/app/snapshot_uploader.py", "--loop"]
