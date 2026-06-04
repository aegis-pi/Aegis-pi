from datetime import timedelta

from cloud_infra.status import section_status, worst_status
from cloud_infra.time_utils import format_utc, parse_utc


def collect_fast(config: dict, now) -> dict:
    errors = []
    backend_runtime = _collect_backend_runtime(config, now, errors)
    data_pipeline = _collect_data_pipeline(config, now, errors)
    factory_freshness = _collect_factory_freshness(config, errors)

    return {
        "backend_runtime": backend_runtime,
        "data_pipeline": data_pipeline,
        "factory_freshness": factory_freshness,
        "errors": errors,
    }


def _collect_backend_runtime(config: dict, now, errors: list[dict]) -> dict:
    ecs = _safe(
        "ecs",
        lambda: _ecs_summary(config),
        errors,
        {
            "cluster_name": config["ecs_cluster_name"],
            "service_name": config["ecs_service_name"],
        },
    )
    ecs_metrics = _safe("ecs_cloudwatch", lambda: _ecs_metrics(config, now), errors, {})
    ecs.update(ecs_metrics)

    alb = _safe(
        "alb",
        lambda: _alb_summary(config, now, ecs),
        errors,
        {"target_group_name": config["target_group_name"]},
    )

    ecs_status = _ecs_status(ecs, config)
    alb_status = _alb_status(alb, config)
    return {
        "status": section_status(ecs_status, alb_status),
        "ecs": ecs,
        "alb": alb,
    }


def _ecs_summary(config: dict) -> dict:
    client = _boto3_client("ecs")
    response = client.describe_services(
        cluster=config["ecs_cluster_name"],
        services=[config["ecs_service_name"]],
    )
    failures = response.get("failures") or []
    services = response.get("services") or []
    if failures or not services:
        return {
            "cluster_name": config["ecs_cluster_name"],
            "service_name": config["ecs_service_name"],
            "desired_count": 0,
            "running_count": 0,
            "pending_count": 0,
            "status": "UNKNOWN",
            "failures": failures,
        }
    service = services[0]
    return {
        "cluster_name": config["ecs_cluster_name"],
        "service_name": config["ecs_service_name"],
        "status": service.get("status"),
        "desired_count": service.get("desiredCount", 0),
        "running_count": service.get("runningCount", 0),
        "pending_count": service.get("pendingCount", 0),
        "load_balancers": service.get("loadBalancers") or [],
    }


def _ecs_metrics(config: dict, now) -> dict:
    queries = [
        _metric_query("ecs_cpu_avg", "AWS/ECS", "CPUUtilization", "Average", [
            {"Name": "ClusterName", "Value": config["ecs_cluster_name"]},
            {"Name": "ServiceName", "Value": config["ecs_service_name"]},
        ]),
        _metric_query("ecs_cpu_max", "AWS/ECS", "CPUUtilization", "Maximum", [
            {"Name": "ClusterName", "Value": config["ecs_cluster_name"]},
            {"Name": "ServiceName", "Value": config["ecs_service_name"]},
        ]),
        _metric_query("ecs_mem_avg", "AWS/ECS", "MemoryUtilization", "Average", [
            {"Name": "ClusterName", "Value": config["ecs_cluster_name"]},
            {"Name": "ServiceName", "Value": config["ecs_service_name"]},
        ]),
        _metric_query("ecs_mem_max", "AWS/ECS", "MemoryUtilization", "Maximum", [
            {"Name": "ClusterName", "Value": config["ecs_cluster_name"]},
            {"Name": "ServiceName", "Value": config["ecs_service_name"]},
        ]),
    ]
    values = _get_metric_values(queries, now, config["metric_window_minutes"])
    return {
        "cpu_utilization_avg": values.get("ecs_cpu_avg"),
        "cpu_utilization_max": values.get("ecs_cpu_max"),
        "memory_utilization_avg": values.get("ecs_mem_avg"),
        "memory_utilization_max": values.get("ecs_mem_max"),
    }


def _alb_summary(config: dict, now, ecs: dict | None = None) -> dict:
    elbv2 = _boto3_client("elbv2")
    target_group_arn = _ecs_target_group_arn(ecs or {})
    if target_group_arn:
        response = elbv2.describe_target_groups(TargetGroupArns=[target_group_arn])
    else:
        response = elbv2.describe_target_groups(Names=[config["target_group_name"]])
    target_group = response["TargetGroups"][0]
    target_group_arn = target_group["TargetGroupArn"]
    target_group_name = target_group.get("TargetGroupName", config["target_group_name"])
    target_group_label = _arn_suffix(target_group_arn, "targetgroup/")
    load_balancer_arns = target_group.get("LoadBalancerArns") or []
    load_balancer_label = None
    if load_balancer_arns:
        load_balancer_label = _arn_suffix(load_balancer_arns[0], "loadbalancer/")

    health = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
    descriptions = health.get("TargetHealthDescriptions", [])
    target_state_counts = _target_state_counts(descriptions)
    alb = {
        "target_group_name": target_group_name,
        "target_group_arn": target_group_arn,
        "healthy_host_count": target_state_counts.get("healthy", 0),
        "unhealthy_host_count": target_state_counts.get("unhealthy", 0),
        "draining_host_count": target_state_counts.get("draining", 0),
        "initial_host_count": target_state_counts.get("initial", 0),
        "unused_host_count": target_state_counts.get("unused", 0),
        "unknown_host_count": target_state_counts.get("unknown", 0),
    }

    if load_balancer_label:
        dimensions = [
            {"Name": "TargetGroup", "Value": target_group_label},
            {"Name": "LoadBalancer", "Value": load_balancer_label},
        ]
        values = _get_metric_values([
            _metric_query("alb_5xx", "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "Sum", dimensions),
            _metric_query("alb_latency_avg", "AWS/ApplicationELB", "TargetResponseTime", "Average", dimensions),
            _metric_query("alb_latency_p95", "AWS/ApplicationELB", "TargetResponseTime", "p95", dimensions),
        ], now, config["metric_window_minutes"])
        alb.update({
            "target_5xx_count_5m": int(values.get("alb_5xx") or 0),
            "target_response_time_avg": values.get("alb_latency_avg"),
            "target_response_time_p95": values.get("alb_latency_p95"),
        })
    return alb


def _collect_data_pipeline(config: dict, now, errors: list[dict]) -> dict:
    lambdas = _safe("lambda_cloudwatch", lambda: _lambda_summaries(config, now), errors, [])
    dynamodb = _safe("dynamodb_cloudwatch", lambda: _dynamodb_summary(config, now), errors, {
        "table_name": config["dynamodb_table_name"],
    })
    schedulers = _safe("scheduler", lambda: _scheduler_summaries(config), errors, [])
    status = worst_status([
        _lambda_status(item) for item in lambdas
    ] + [_dynamodb_status(dynamodb), _scheduler_status(schedulers)])
    return {
        "status": status,
        "lambdas": lambdas,
        "dynamodb": dynamodb,
        "schedulers": schedulers,
    }


def _lambda_summaries(config: dict, now) -> list[dict]:
    result = []
    for name in config["lambda_function_names"]:
        dimensions = [{"Name": "FunctionName", "Value": name}]
        values = _get_metric_values([
            _metric_query(f"{_safe_metric_id(name)}_inv", "AWS/Lambda", "Invocations", "Sum", dimensions),
            _metric_query(f"{_safe_metric_id(name)}_err", "AWS/Lambda", "Errors", "Sum", dimensions),
            _metric_query(f"{_safe_metric_id(name)}_thr", "AWS/Lambda", "Throttles", "Sum", dimensions),
            _metric_query(f"{_safe_metric_id(name)}_dur", "AWS/Lambda", "Duration", "p95", dimensions),
        ], now, config["metric_window_minutes"])
        prefix = _safe_metric_id(name)
        result.append({
            "name": name,
            "invocations_5m": int(values.get(f"{prefix}_inv") or 0),
            "errors_5m": int(values.get(f"{prefix}_err") or 0),
            "throttles_5m": int(values.get(f"{prefix}_thr") or 0),
            "duration_p95_ms": values.get(f"{prefix}_dur"),
        })
    return result


def _dynamodb_summary(config: dict, now) -> dict:
    dimensions = [{"Name": "TableName", "Value": config["dynamodb_table_name"]}]
    values = _get_metric_values([
        _metric_query("ddb_read_throttle", "AWS/DynamoDB", "ReadThrottleEvents", "Sum", dimensions),
        _metric_query("ddb_write_throttle", "AWS/DynamoDB", "WriteThrottleEvents", "Sum", dimensions),
        _metric_query("ddb_system_errors", "AWS/DynamoDB", "SystemErrors", "Sum", dimensions),
    ], now, config["metric_window_minutes"])
    return {
        "table_name": config["dynamodb_table_name"],
        "read_throttle_events_5m": int(values.get("ddb_read_throttle") or 0),
        "write_throttle_events_5m": int(values.get("ddb_write_throttle") or 0),
        "system_errors_5m": int(values.get("ddb_system_errors") or 0),
    }


def _scheduler_summaries(config: dict) -> list[dict]:
    client = _boto3_client("scheduler")
    result = []
    for name in config["scheduler_names"]:
        response = client.get_schedule(Name=name)
        result.append({"name": name, "state": response.get("State", "UNKNOWN")})
    return result


def _collect_factory_freshness(config: dict, errors: list[dict]) -> dict:
    from cloud_infra import dynamo

    factories = []
    for factory_id in config["factory_ids"]:
        try:
            latest = dynamo.get_factory_latest(factory_id)
            factories.append(_factory_summary(factory_id, latest))
        except Exception as exc:
            errors.append({"collector": "factory_freshness", "factory_id": factory_id, "error": str(exc)})
            factories.append({"factory_id": factory_id, "status": "unknown"})
    return {
        "status": worst_status([item.get("pipeline_status") or item.get("status") for item in factories]),
        "factories": factories,
    }


def _factory_summary(factory_id: str, latest: dict) -> dict:
    pipeline = latest.get("pipeline_status") or {}
    risk = latest.get("risk") or {}
    return {
        "factory_id": factory_id,
        "pipeline_status": pipeline.get("status", "unknown"),
        "latest_infra_state_age_seconds": pipeline.get("latest_infra_state_age_seconds"),
        "last_infra_state_at": latest.get("last_infra_state_at"),
        "risk_score": risk.get("score"),
        "risk_level": risk.get("level"),
        "top_causes": risk.get("top_causes") or [],
    }


def _get_metric_values(queries: list[dict], now, minutes: int) -> dict:
    client = _boto3_client("cloudwatch")
    response = client.get_metric_data(
        MetricDataQueries=queries,
        StartTime=now - timedelta(minutes=minutes),
        EndTime=now,
        ScanBy="TimestampDescending",
    )
    values = {}
    for item in response.get("MetricDataResults", []):
        metric_values = item.get("Values") or []
        values[item["Id"]] = round(float(metric_values[0]), 4) if metric_values else None
    return values


def _metric_query(metric_id: str, namespace: str, metric_name: str, stat: str, dimensions: list[dict]) -> dict:
    return {
        "Id": metric_id,
        "MetricStat": {
            "Metric": {
                "Namespace": namespace,
                "MetricName": metric_name,
                "Dimensions": dimensions,
            },
            "Period": 60,
            "Stat": stat,
        },
        "ReturnData": True,
    }


def _ecs_status(ecs: dict, config: dict) -> str:
    desired = int(ecs.get("desired_count") or 0)
    running = int(ecs.get("running_count") or 0)
    if desired > 0 and running == 0:
        return "critical"
    if running < desired:
        return "warning"
    if (ecs.get("cpu_utilization_max") or 0) >= config["ecs_cpu_warning_percent"]:
        return "warning"
    if (ecs.get("memory_utilization_max") or 0) >= config["ecs_memory_warning_percent"]:
        return "warning"
    return "normal"


def _alb_status(alb: dict, config: dict) -> str:
    if alb.get("status") == "unknown" and "healthy_host_count" not in alb:
        return "unknown"
    healthy = int(alb.get("healthy_host_count") or 0)
    if healthy == 0:
        return "critical"
    if int(alb.get("target_5xx_count_5m") or 0) > 0:
        return "warning"
    if (alb.get("target_response_time_p95") or alb.get("target_response_time_avg") or 0) >= config["alb_latency_warning_seconds"]:
        return "warning"
    return "normal"


def _lambda_status(item: dict) -> str:
    if int(item.get("errors_5m") or 0) > 0 or int(item.get("throttles_5m") or 0) > 0:
        return "warning"
    return "normal"


def _dynamodb_status(item: dict) -> str:
    if int(item.get("system_errors_5m") or 0) > 0:
        return "critical"
    if int(item.get("read_throttle_events_5m") or 0) > 0 or int(item.get("write_throttle_events_5m") or 0) > 0:
        return "warning"
    return "normal"


def _scheduler_status(items: list[dict]) -> str:
    if not items:
        return "unknown"
    disabled = [item for item in items if item.get("state") != "ENABLED"]
    return "warning" if disabled else "normal"


def _safe(collector: str, func, errors: list[dict], fallback):
    try:
        return func()
    except Exception as exc:
        errors.append({"collector": collector, "error": str(exc)})
        if isinstance(fallback, dict):
            return {**fallback, "status": "unknown"}
        return fallback


def _arn_suffix(arn: str, marker: str) -> str:
    return arn.split(marker, 1)[1]


def _target_state_counts(descriptions: list[dict]) -> dict[str, int]:
    counts = {
        "healthy": 0,
        "unhealthy": 0,
        "draining": 0,
        "initial": 0,
        "unused": 0,
        "unknown": 0,
    }
    for item in descriptions:
        state = (item.get("TargetHealth") or {}).get("State") or "unknown"
        counts[state if state in counts else "unknown"] += 1
    return counts


def _ecs_target_group_arn(ecs: dict) -> str | None:
    for load_balancer in ecs.get("load_balancers") or []:
        target_group_arn = load_balancer.get("targetGroupArn")
        if target_group_arn:
            return target_group_arn
    return None


def _safe_metric_id(name: str) -> str:
    chars = [char.lower() if char.isalnum() else "_" for char in name]
    result = "".join(chars).strip("_")
    if not result or not result[0].isalpha():
        result = f"m_{result}"
    return result[:100]


def _boto3_client(service: str):
    import boto3

    return boto3.client(service)
