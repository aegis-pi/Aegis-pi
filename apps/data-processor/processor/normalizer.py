def normalize_factory_state(payload: dict) -> dict:
    sensor = payload.get("sensor", {})
    ai = payload.get("ai_result", {})

    return {
        "aggregation_window_seconds": int(payload.get("aggregation_window_seconds", 0)),
        "temperature_celsius": _float(sensor.get("temperature_celsius_avg")),
        "humidity_percent": _float(sensor.get("humidity_percent_avg")),
        "pressure_hpa": _float(sensor.get("pressure_hpa_avg")),
        "sample_count": int(sensor.get("sample_count", 0)),
        "fire_score": _float(ai.get("fire_score")),
        "fall_score": _float(ai.get("fall_score")),
        "bend_score": _float(ai.get("bend_score")),
        "abnormal_sound": str(ai.get("abnormal_sound", "none")),
        "ai_sample_count": int(ai.get("sample_count", 0)),
    }


def normalize_infra_state(payload: dict) -> dict:
    heartbeat = payload.get("heartbeat", {})
    cluster = payload.get("cluster", {})
    node_summary = payload.get("node_summary", {})
    workload_summary = payload.get("workload_summary", {})
    nodes = payload.get("nodes", [])
    workloads = payload.get("workloads", [])
    devices = payload.get("devices", {})

    nodes_ready = int(node_summary.get("ready", _count_ready_nodes(nodes)))
    nodes_total = int(node_summary.get("total", len(nodes)))
    workloads_running = int(workload_summary.get("running", _count_ready_workloads(workloads)))
    workloads_total = int(workload_summary.get("total", len(workloads)))

    return {
        "agent_status": str(heartbeat.get("agent_status", "unknown")),
        "last_successful_publish_at": heartbeat.get("last_successful_publish_at"),
        "last_spool_write_status": heartbeat.get("last_spool_write_status"),
        "last_spool_write_at": heartbeat.get("last_spool_write_at"),
        "publish_sequence": int(heartbeat.get("publish_sequence", 0)),
        "cluster_name": str(cluster.get("cluster_name", "")),
        "kubernetes_version": str(cluster.get("kubernetes_version", "")),
        "node_summary": {
            "total": nodes_total,
            "ready": nodes_ready,
            "not_ready": int(node_summary.get("not_ready", max(nodes_total - nodes_ready, 0))),
        },
        "nodes_total": nodes_total,
        "nodes_ready": nodes_ready,
        "nodes": [_normalize_node(n) for n in nodes],
        "workload_summary": {
            "total": workloads_total,
            "running": workloads_running,
            "not_running": int(workload_summary.get("not_running", max(workloads_total - workloads_running, 0))),
        },
        "pods_ready": workloads_running,
        "pods_total": workloads_total,
        "workloads": [_normalize_workload(w) for w in workloads],
        "devices": _normalize_devices(devices),
    }


def normalize_image_snapshot(payload: dict) -> dict:
    return {
        "event_type": str(payload.get("event_type", "UNKNOWN")),
        "content_type": str(payload.get("content_type", "")),
        "size_bytes": int(payload.get("size_bytes", 0)),
        "sha256": str(payload.get("sha256", "")),
        "s3_bucket": str(payload.get("s3_bucket", "")),
        "s3_key": str(payload.get("s3_key", "")),
        "local_path": payload.get("local_path"),
        "upload_status": str(payload.get("upload_status", "uploaded")),
    }


def _normalize_node(node: dict) -> dict:
    ready = _ready_value(node)
    return {
        "node_id": str(node.get("node_id", node.get("name", ""))),
        "role": str(node.get("role", "")),
        "ready": ready,
        "status": "Ready" if ready else "NotReady",
        "cpu_usage_percent": _nullable_float(node.get("cpu_usage_percent")),
        "memory_usage_percent": _nullable_float(node.get("memory_usage_percent")),
        "disk_usage_percent": _nullable_float(node.get("disk_usage_percent")),
        "network_reachability": str(node.get("network_reachability", "unknown")),
    }


def _normalize_workload(w: dict) -> dict:
    ready = bool(w.get("ready", False))
    return {
        "namespace": str(w.get("namespace", "")),
        "name": str(w.get("name", "")),
        "status": str(w.get("status", "unknown")),
        "ready": ready,
        "containers_ready": int(w.get("containers_ready", 0)),
        "containers_total": int(w.get("containers_total", 0)),
        "restart_count": int(w.get("restart_count", 0)),
        "node_id": str(w.get("node_id", "unknown")),
    }


def _normalize_devices(devices: dict) -> dict:
    result = {}
    for name, info in devices.items():
        available = info.get("available")
        if available is None:
            status = str(info.get("status", "unknown"))
        else:
            status = "available" if bool(available) else "unavailable"
        result[name] = {
            "available": bool(available) if available is not None else None,
            "status": status,
            "last_seen_at": info.get("last_seen_at"),
        }
    return result


def _count_ready_nodes(nodes: list[dict]) -> int:
    return sum(1 for node in nodes if _ready_value(node))


def _count_ready_workloads(workloads: list[dict]) -> int:
    return sum(1 for workload in workloads if bool(workload.get("ready", False)) or workload.get("status") == "Running")


def _ready_value(node: dict) -> bool:
    if "ready" in node:
        return bool(node.get("ready"))
    return node.get("status") == "Ready"


def _nullable_float(value) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _float(value) -> float:
    try:
        return round(float(value), 4) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
