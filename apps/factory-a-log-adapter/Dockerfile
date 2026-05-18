FROM python:3.13-alpine

WORKDIR /app

RUN addgroup -S aegis && adduser -S -G aegis -u 10001 aegis

COPY factory_a_log_adapter.py /app/factory_a_log_adapter.py

ENV AEGIS_FACTORY_ID=factory-a \
    AEGIS_ENVIRONMENT_TYPE=physical-rpi \
    AEGIS_INPUT_MODULE_TYPE=sensor \
    AEGIS_INFLUXDB_URL=http://influxdb-svc.monitoring.svc.cluster.local:8086 \
    AEGIS_INFLUXDB_DATABASE=safe_edge_db \
    AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox \
    PYTHONUNBUFFERED=1

USER aegis

CMD ["python", "/app/factory_a_log_adapter.py", "--loop"]
