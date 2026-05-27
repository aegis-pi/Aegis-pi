# Factory A Log Adapter

`factory-a-log-adapter` reads existing factory-a data sources and writes canonical AEGIS JSON files to the local spool/outbox. It does not publish to AWS IoT Core.

## Inputs

The adapter is read-only. It does not access `/dev/i2c-1`, camera, or microphone devices directly.

| Source | Use |
| --- | --- |
| InfluxDB `safe_edge_db.environment_data` | BME280 temperature, humidity, pressure averages |
| InfluxDB `safe_edge_db.ai_detection` | fire/fall/bend scores |
| InfluxDB `safe_edge_db.acoustic_detection` | `abnormal_sound` label |
| Kubernetes API | node, workload, and device summary state |
| Prometheus `prometheus-svc.monitoring.svc.cluster.local:9090` | node exporter CPU, memory, and root filesystem usage |

`abnormal_sound` keeps the current canonical schema. The adapter maps recent `acoustic_detection` rows as follows:

```text
sum(is_danger) == 0 or no samples -> "none"
sum(is_danger) > 0 and event_type is usable -> event_type
sum(is_danger) > 0 and event_type is empty/None -> "abnormal_sound"
```

## Configuration

| Environment variable | Default |
| --- | --- |
| `AEGIS_FACTORY_ID` | `factory-a` |
| `AEGIS_ENVIRONMENT_TYPE` | `physical-rpi` |
| `AEGIS_INPUT_MODULE_TYPE` | `sensor` |
| `AEGIS_INFLUXDB_URL` | `http://influxdb-svc.monitoring.svc.cluster.local:8086` |
| `AEGIS_INFLUXDB_DATABASE` | `safe_edge_db` |
| `AEGIS_PROMETHEUS_URL` | `http://prometheus-svc.monitoring.svc.cluster.local:9090` |
| `AEGIS_OUTBOX_DIR` | `/var/lib/aegis/outbox` |
| `AEGIS_FACTORY_STATE_WINDOW_SECONDS` | `3` |
| `AEGIS_FACTORY_STATE_INTERVAL_SECONDS` | `3` |
| `AEGIS_INFRA_STATE_INTERVAL_SECONDS` | `20` |
| `AEGIS_INFLUXDB_FALLBACK_SAMPLE_LIMIT` | `5` |
| `AEGIS_WORKLOADS` | `monitoring/bme280-sensor,ai-apps/safe-edge-integrated-ai,ai-apps/safe-edge-audio,monitoring/influxdb,monitoring/prometheus,monitoring/grafana` |

## Local Run

```bash
python3 apps/factory-a-log-adapter/factory_a_log_adapter.py --once factory_state --no-write --pretty
```

Write one `factory_state` and one `infra_state` candidate to a local outbox:

```bash
AEGIS_OUTBOX_DIR=/tmp/aegis-outbox \
  python3 apps/factory-a-log-adapter/factory_a_log_adapter.py --once all
```

Run continuously with the M4 default periods:

```bash
python3 apps/factory-a-log-adapter/factory_a_log_adapter.py --loop
```

The file name is `{message_id}.json`. The adapter writes through `outbox/tmp` and atomically renames the file into the outbox root.

## Tests

```bash
python3 -m unittest discover -s apps/factory-a-log-adapter/tests
```
