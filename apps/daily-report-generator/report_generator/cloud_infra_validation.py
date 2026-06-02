def validate_cloud_infra_report_invariants(context: dict, markdown: str) -> list[str]:
    values = [
        context.get("target_id"),
        context.get("report_date"),
        context.get("overall_status"),
    ]
    dq = context.get("data_quality", {})
    for key in (
        "fast_actual_count",
        "fast_expected_count",
        "fast_collection_rate",
        "slow_actual_count",
        "slow_expected_count",
        "slow_collection_rate",
    ):
        if dq.get(key) is not None:
            values.append(str(dq[key]))
    backend = context.get("backend_runtime", {})
    for key in ("ecs_running_count_min", "ecs_desired_count"):
        if backend.get(key) is not None:
            values.append(str(backend[key]))
    eks = context.get("eks_management", {})
    for key in ("nodes_ready_min", "nodes_total_max"):
        if eks.get(key) is not None:
            values.append(str(eks[key]))
    argo = context.get("argocd", {})
    for key in ("synced_min", "applications_total_max"):
        if argo.get(key) is not None:
            values.append(str(argo[key]))

    errors = []
    for value in values:
        if value and value not in markdown:
            errors.append(f"missing invariant value: {value}")
    return errors
