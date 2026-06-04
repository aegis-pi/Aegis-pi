from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SEVERITY_RANK = {
    "normal": 0,
    "safe": 0,
    "unknown": 1,
    "warning": 2,
    "danger": 3,
    "critical": 3,
}


@dataclass(frozen=True)
class Alert:
    scope: str
    source_type: str
    severity: str
    reason: str
    status: str
    source_updated_at: str
    source_key: str
    fingerprint_status: str | None = None
    confirmation_observations: int = 1
    confirmation_window_seconds: int = 0
    score: float | int | None = None
    title: str = ""
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def pk(self) -> str:
        return f"ALERT#{self.scope}"

    @property
    def sk(self) -> str:
        return f"{self.severity}#{self.reason}#{self.fingerprint_status or self.status}"


def evaluate(source, snapshot: dict) -> list[Alert]:
    if source.source_type == "factory_state_snapshot":
        return _factory_alerts(source, snapshot)
    if source.source_type == "cloud_infra_fast":
        return _cloud_fast_alerts(source, snapshot)
    if source.source_type == "cloud_infra_slow":
        return _cloud_slow_alerts(source, snapshot)
    return []


def severity_rank(value: str | None) -> int:
    return SEVERITY_RANK.get((value or "unknown").lower(), SEVERITY_RANK["unknown"])


def _factory_alerts(source, snapshot: dict) -> list[Alert]:
    factory_id = snapshot.get("factory_id") or source.scope
    updated_at = snapshot.get("updated_at") or (snapshot.get("risk") or {}).get("calculated_at") or ""
    risk = snapshot.get("risk") or {}
    pipeline = snapshot.get("pipeline_status") or {}
    risk_level = _normalize_factory_severity(risk.get("level"))
    pipeline_status = (pipeline.get("status") or "unknown").lower()
    pipeline_alerting = pipeline_status in {"warning", "critical"}
    alerts: list[Alert] = []

    if risk_level in {"warning", "danger"}:
        alert_causes = [
            cause
            for cause in risk.get("top_causes") or []
            if not (pipeline_alerting and _is_pipeline_freshness(cause))
        ]
        if alert_causes or not pipeline_alerting:
            top_cause = _top_cause(alert_causes)
            reason = _slug(top_cause.get("reason") or top_cause.get("field") or "risk_level")
            alerts.append(Alert(
                scope=factory_id,
                source_type=source.source_type,
                severity=risk_level,
                reason=reason,
                status=pipeline_status,
                source_updated_at=updated_at,
                source_key=source.key,
                fingerprint_status="state_snapshot",
                score=risk.get("score"),
                title=f"[AEGIS Alert] {factory_id} {risk_level}",
                summary={
                    "pipeline_status": pipeline_status,
                    "top_causes": alert_causes,
                    "gates": [
                        gate
                        for gate in risk.get("gates") or []
                        if not (pipeline_alerting and _is_pipeline_freshness(gate))
                    ],
                },
            ))

    if pipeline_alerting:
        severity = "danger" if pipeline_status == "critical" else "warning"
        alerts.append(Alert(
            scope=factory_id,
            source_type=source.source_type,
            severity=severity,
            reason="pipeline_status",
            status=pipeline_status,
            source_updated_at=updated_at,
            source_key=source.key,
            score=risk.get("score"),
            title=f"[AEGIS Alert] {factory_id} {severity}",
            summary={"pipeline_status": pipeline_status, "latest_infra_state_age_seconds": pipeline.get("latest_infra_state_age_seconds")},
        ))

    for cause in risk.get("top_causes") or []:
        if pipeline_alerting and _is_pipeline_freshness(cause):
            continue
        if _normalize_factory_severity(cause.get("severity")) == "danger":
            alerts.append(Alert(
                scope=factory_id,
                source_type=source.source_type,
                severity="danger",
                reason=_slug(cause.get("reason") or cause.get("field") or "danger_cause"),
                status=pipeline_status,
                source_updated_at=updated_at,
                source_key=source.key,
                fingerprint_status="state_snapshot",
                score=risk.get("score"),
                title=f"[AEGIS Alert] {factory_id} danger",
                summary={"pipeline_status": pipeline_status, "top_causes": [cause]},
            ))

    for gate in risk.get("gates") or []:
        if pipeline_alerting and _is_pipeline_freshness(gate):
            continue
        gate_severity = _normalize_factory_severity(gate.get("severity") or gate.get("level"))
        if gate_severity == "danger":
            alerts.append(Alert(
                scope=factory_id,
                source_type=source.source_type,
                severity="danger",
                reason=_slug(gate.get("reason") or gate.get("field") or gate.get("gate") or "danger_gate"),
                status=pipeline_status,
                source_updated_at=updated_at,
                source_key=source.key,
                fingerprint_status="state_snapshot",
                score=risk.get("score"),
                title=f"[AEGIS Alert] {factory_id} danger",
                summary={"pipeline_status": pipeline_status, "gates": [gate]},
            ))

    return _dedupe_alerts(alerts)


def _cloud_fast_alerts(source, snapshot: dict) -> list[Alert]:
    fast = snapshot.get("fast") or {}
    updated_at = snapshot.get("fast_updated_at") or snapshot.get("updated_at") or ""
    alerts: list[Alert] = []
    specific_sections: set[str] = set()

    data_pipeline = fast.get("data_pipeline") or {}
    data_pipeline_severity = _cloud_specific_severity(_status(data_pipeline.get("status")))
    for item in data_pipeline.get("lambdas") or []:
        if _number(item.get("errors_5m")) > 0:
            specific_sections.add("data_pipeline")
            alerts.append(_cloud_alert(source, updated_at, data_pipeline_severity, "data_pipeline_lambda_errors", "fast", {"lambda": item}))
        if _number(item.get("throttles_5m")) > 0:
            specific_sections.add("data_pipeline")
            alerts.append(_cloud_alert(source, updated_at, data_pipeline_severity, "data_pipeline_lambda_throttles", "fast", {"lambda": item}))

    dynamodb = data_pipeline.get("dynamodb") or {}
    if _number(dynamodb.get("read_throttle_events_5m")) > 0 or _number(dynamodb.get("write_throttle_events_5m")) > 0:
        specific_sections.add("data_pipeline")
        alerts.append(_cloud_alert(source, updated_at, data_pipeline_severity, "dynamodb_throttles", "fast", {"dynamodb": dynamodb}))

    backend_runtime = fast.get("backend_runtime") or {}
    backend_runtime_severity = _cloud_specific_severity(_status(backend_runtime.get("status")))
    alb = backend_runtime.get("alb") or {}
    if _number(alb.get("unhealthy_host_count")) > 0:
        specific_sections.add("backend_runtime")
        alerts.append(_cloud_alert(source, updated_at, backend_runtime_severity, "alb_unhealthy_hosts", "fast", {"alb": alb}))

    collector_errors = fast.get("errors") or []
    for error in collector_errors:
        alerts.append(_cloud_alert(source, updated_at, "warning", _error_reason(error), "fast", {"error": error}))

    for section_name in ("backend_runtime", "data_pipeline"):
        section = fast.get(section_name) or {}
        status = _status(section.get("status"))
        if status == "normal" or section_name in specific_sections:
            continue
        if _suppress_unknown_when_collector_failed(status, collector_errors):
            continue
        alerts.append(_cloud_alert(source, updated_at, status, f"{section_name}_{status}", "fast", {section_name: section}))

    return _dedupe_alerts(alerts)


def _cloud_slow_alerts(source, snapshot: dict) -> list[Alert]:
    slow = snapshot.get("slow") or {}
    eks = slow.get("eks_management") or {}
    updated_at = snapshot.get("slow_updated_at") or snapshot.get("updated_at") or ""
    alerts: list[Alert] = []
    collector_errors = slow.get("errors") or []
    has_eks_specific_alert = False

    for error in collector_errors:
        alerts.append(_cloud_alert(source, updated_at, "warning", _error_reason(error), "slow", {"error": error}))

    storage = slow.get("storage_freshness") or {}
    storage_status = _status(storage.get("status"))
    if storage_status != "normal":
        alerts.append(_cloud_alert(source, updated_at, _cloud_severity(storage_status), f"storage_freshness_{storage_status}", "slow", {"storage_freshness": storage}))

    cluster = eks.get("cluster") or {}
    if cluster.get("status") and cluster.get("status") != "ACTIVE":
        has_eks_specific_alert = True
        alerts.append(_cloud_alert(source, updated_at, "danger", "eks_cluster_not_active", "slow", {"cluster": cluster}))

    for nodegroup in eks.get("nodegroups") or []:
        if nodegroup.get("status") and nodegroup.get("status") != "ACTIVE":
            has_eks_specific_alert = True
            alerts.append(_cloud_alert(source, updated_at, "danger", "eks_nodegroup_not_active", "slow", {"nodegroup": nodegroup}))

    autoscaling = eks.get("autoscaling") or {}
    if _number(autoscaling.get("healthy_instances")) < _number(autoscaling.get("desired_capacity")):
        has_eks_specific_alert = True
        alerts.append(_cloud_alert(source, updated_at, "danger", "autoscaling_unhealthy_instances", "slow", {"autoscaling": autoscaling}))

    for section_name in ("nodes", "pods", "argocd"):
        section = eks.get(section_name) or {}
        status = _status(section.get("status"))
        if status != "normal" and not _suppress_unknown_when_collector_failed(status, collector_errors):
            has_eks_specific_alert = True
            alerts.append(_cloud_alert(source, updated_at, _cloud_severity(status), f"{section_name}_{status}", "slow", {section_name: section}))

    eks_status = _status(eks.get("status"))
    if (
        eks_status != "normal"
        and not has_eks_specific_alert
        and not _suppress_unknown_when_collector_failed(eks_status, collector_errors)
    ):
        alerts.append(_cloud_alert(source, updated_at, _cloud_severity(eks_status), f"eks_management_{eks_status}", "slow", {"eks_management": eks}))

    return _dedupe_alerts(alerts)


def _cloud_alert(source, updated_at: str, severity: str, reason: str, status: str, summary: dict) -> Alert:
    severity = "danger" if severity == "critical" else severity
    confirmation_observations, confirmation_window_seconds = _cloud_confirmation_policy(
        source.source_type,
        severity,
        reason,
    )
    return Alert(
        scope=source.scope,
        source_type=source.source_type,
        severity=severity,
        reason=_slug(reason),
        status=status,
        source_updated_at=updated_at,
        source_key=source.key,
        confirmation_observations=confirmation_observations,
        confirmation_window_seconds=confirmation_window_seconds,
        title=f"[AEGIS Cloud Infra Alert] {severity}",
        summary=summary,
    )


def _dedupe_alerts(alerts: list[Alert]) -> list[Alert]:
    result = {}
    for alert in alerts:
        result[(alert.pk, alert.sk)] = alert
    return list(result.values())


def _normalize_factory_severity(value: str | None) -> str:
    value = (value or "safe").lower()
    if value == "critical":
        return "danger"
    return value


def _cloud_severity(status: str) -> str:
    if status == "critical":
        return "danger"
    if status in {"warning", "unknown"}:
        return "warning"
    return status


def _cloud_specific_severity(section_status: str) -> str:
    if section_status == "critical":
        return "danger"
    return "warning"


def _cloud_confirmation_policy(source_type: str, severity: str, reason: str) -> tuple[int, int]:
    if severity != "warning":
        return 1, 0

    reason = _slug(reason)
    if source_type == "cloud_infra_fast" and reason in {
        "backend_runtime_warning",
        "data_pipeline_warning",
        "data_pipeline_lambda_errors",
    }:
        return 2, 90

    if source_type == "cloud_infra_slow" and reason in {
        "eks_management_warning",
        "pods_warning",
    }:
        return 2, 450

    return 1, 0


def _suppress_unknown_when_collector_failed(status: str, collector_errors: list[dict]) -> bool:
    return status == "unknown" and bool(collector_errors)


def _status(value: str | None) -> str:
    return (value or "unknown").lower()


def _top_cause(causes: list[dict]) -> dict:
    if not causes:
        return {}
    return max(causes, key=lambda item: _number(item.get("contribution")))


def _is_pipeline_freshness(item: dict) -> bool:
    reason = str(item.get("reason") or item.get("name") or "").lower()
    field = str(item.get("field") or "").lower()
    return field == "data_freshness" or reason.startswith(("data_freshness", "pipeline_status"))


def _error_reason(error: dict) -> str:
    collector = error.get("collector") or "collector_error"
    message = (error.get("error") or "").lower()
    if "unauthorized" in message or "401" in message:
        return f"{collector}_unauthorized"
    return f"{collector}_error"


def _slug(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    chars = [ch if ch.isalnum() else "_" for ch in text]
    return "_".join("".join(chars).split("_")) or "unknown"


def _number(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
