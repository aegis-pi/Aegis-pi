def validate_report_invariants(context: dict, markdown: str) -> list[str]:
    errors = []
    invariant_values = [context.get("factory_id"), context.get("report_date")]
    risk = context.get("risk", {})
    for key in ("min_score", "max_score"):
        if risk.get(key) is not None:
            invariant_values.append(str(risk[key]))
    data_quality = context.get("data_quality", {})
    for key in (
        "factory_state_actual_count",
        "factory_state_expected_count",
        "factory_state_collection_rate",
        "infra_state_actual_count",
        "infra_state_expected_count",
        "infra_state_collection_rate",
    ):
        if data_quality.get(key) is not None:
            invariant_values.append(str(data_quality[key]))
    for value in invariant_values:
        if value and value not in markdown:
            errors.append(f"missing invariant value: {value}")
    return errors
