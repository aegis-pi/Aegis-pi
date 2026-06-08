from processor.normalizer import normalize_image_snapshot, normalize_infra_state


def test_normalize_infra_state_preserves_canonical_schema():
    payload = {
        "heartbeat": {
            "agent_status": "alive",
            "last_spool_write_at": None,
            "last_spool_write_status": "unknown",
        },
        "node_summary": {"not_ready": 0, "ready": 3, "total": 3},
        "nodes": [
            {
                "node_id": "master",
                "role": "control-plane",
                "ready": True,
                "cpu_usage_percent": None,
                "memory_usage_percent": None,
                "disk_usage_percent": None,
                "network_reachability": "unknown",
            },
            {
                "node_id": "worker1",
                "role": "failover-standby",
                "ready": True,
                "cpu_usage_percent": 12.34567,
                "memory_usage_percent": 45.0,
                "disk_usage_percent": 67,
                "network_reachability": "ok",
            },
            {
                "node_id": "worker2",
                "role": "sensor-ai-audio-preferred",
                "ready": True,
                "cpu_usage_percent": None,
                "memory_usage_percent": None,
                "disk_usage_percent": None,
                "network_reachability": "unknown",
            },
        ],
        "workload_summary": {"not_running": 0, "running": 1, "total": 1},
        "workloads": [
            {
                "namespace": "monitoring",
                "name": "bme280-sensor",
                "node_id": "worker2",
                "ready": True,
                "restart_count": 12,
                "status": "Running",
            }
        ],
        "devices": {
            "bme280": {"available": True, "last_seen_at": "2026-05-27T02:44:48Z"},
            "camera": {"available": False, "last_seen_at": None},
        },
    }

    normalized = normalize_infra_state(payload)

    assert normalized["nodes_total"] == 3
    assert normalized["nodes_ready"] == 3
    assert normalized["node_summary"] == {"total": 3, "ready": 3, "not_ready": 0}
    assert normalized["nodes"][0] == {
        "node_id": "master",
        "role": "control-plane",
        "ready": True,
        "status": "Ready",
        "cpu_usage_percent": None,
        "memory_usage_percent": None,
        "disk_usage_percent": None,
        "network_reachability": "unknown",
    }
    assert normalized["nodes"][1]["cpu_usage_percent"] == 12.3457
    assert normalized["workload_summary"] == {"total": 1, "running": 1, "not_running": 0}
    assert normalized["pods_ready"] == 1
    assert normalized["pods_total"] == 1
    assert normalized["workloads"][0] == {
        "namespace": "monitoring",
        "name": "bme280-sensor",
        "status": "Running",
        "ready": True,
        "containers_ready": 0,
        "containers_total": 0,
        "restart_count": 12,
        "node_id": "worker2",
    }
    assert normalized["devices"]["bme280"] == {
        "available": True,
        "status": "available",
        "last_seen_at": "2026-05-27T02:44:48Z",
    }
    assert normalized["devices"]["camera"] == {
        "available": False,
        "status": "unavailable",
        "last_seen_at": None,
    }


def test_normalize_image_snapshot_metadata():
    normalized = normalize_image_snapshot(
        {
            "event_type": "FALLEN",
            "content_type": "image/jpeg",
            "size_bytes": 60345,
            "sha256": "a" * 64,
            "s3_bucket": "aegis-bucket-data",
            "s3_key": "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
            "local_path": "/var/lib/safe-edge/snapshots/260608094235_event_FALLEN.jpg",
            "upload_status": "uploaded",
        }
    )

    assert normalized == {
        "event_type": "FALLEN",
        "content_type": "image/jpeg",
        "size_bytes": 60345,
        "sha256": "a" * 64,
        "s3_bucket": "aegis-bucket-data",
        "s3_key": "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
        "local_path": "/var/lib/safe-edge/snapshots/260608094235_event_FALLEN.jpg",
        "upload_status": "uploaded",
    }
