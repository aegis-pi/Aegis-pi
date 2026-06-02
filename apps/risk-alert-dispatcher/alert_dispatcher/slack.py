from __future__ import annotations

import json
import os
import urllib.request

from alert_dispatcher.rules import Alert


class SlackNotConfigured(RuntimeError):
    pass


def send(alert: Alert) -> dict:
    webhook_url = _webhook_url(alert)
    payload = {"text": format_message(alert)}
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.environ.get("SLACK_HTTP_TIMEOUT_SECONDS", "4"))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return {"status_code": response.status, "body": body}


def format_message(alert: Alert) -> str:
    title = "AEGIS Alert | 위험 알림" if alert.severity == "danger" else "AEGIS Alert | 경고 알림"
    severity_label = _severity_label(alert.severity)
    source_label = _source_label(alert.source_type)
    status_label = alert.summary.get("pipeline_status") or alert.status

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        title,
        "",
        "무엇이 문제인가요?",
        f"{alert.scope}에서 {severity_label} 조건이 감지되었습니다.",
        "",
        "현재 상태",
        f"- 심각도: {severity_label}",
        f"- 공장/대상: {alert.scope}",
        f"- 수집/스냅샷: {source_label}",
        f"- 상태: {status_label}",
    ]
    if alert.score is not None:
        lines.append(f"- 위험 점수: {alert.score}")

    lines.extend([
        "",
        "왜 발생했나요?",
        f"- 원인: {alert.reason}",
    ])

    top_causes = alert.summary.get("top_causes") or []
    if top_causes:
        lines.append("")
        lines.append("주요 원인")
        for idx, cause in enumerate(top_causes[:3], start=1):
            lines.append(f"{idx}. 항목: {cause.get('field', '-')}")
            lines.append(f"   원인: {cause.get('reason', '-')}")
            lines.append(f"   현재 값: {cause.get('value', '-')}")
            if cause.get("contribution") is not None:
                lines.append(f"   영향도: {cause.get('contribution')}")
            if cause.get("severity"):
                lines.append(f"   등급: {_severity_label(cause.get('severity'))}")

    gates = alert.summary.get("gates") or []
    if gates:
        lines.append("")
        lines.append("위험 판단 기준")
        for idx, gate in enumerate(gates[:3], start=1):
            lines.append(f"{idx}. {gate.get('reason') or gate.get('gate') or gate}")

    error = alert.summary.get("error")
    if error:
        lines.append("")
        lines.append("오류 상세")
        lines.append(f"- {error.get('error') or error}")

    for section_name, label in (
        ("lambda", "Lambda 상태"),
        ("dynamodb", "DynamoDB 상태"),
        ("alb", "ALB 상태"),
        ("cluster", "EKS 클러스터 상태"),
        ("nodegroup", "EKS 노드그룹 상태"),
        ("autoscaling", "Auto Scaling 상태"),
    ):
        section = alert.summary.get(section_name)
        if section:
            lines.append("")
            lines.append(label)
            lines.extend(_section_lines(section))

    lines.extend([
        "",
        "확인할 데이터",
        alert.source_key,
        "",
        "중복 알림 제어",
        "동일 조건은 cooldown 동안 재전송되지 않습니다.",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ])
    return "\n".join(lines)


def _severity_label(value: str | None) -> str:
    labels = {
        "danger": "위험(DANGER)",
        "critical": "위험(CRITICAL)",
        "warning": "경고(WARNING)",
        "normal": "정상(NORMAL)",
        "safe": "정상(SAFE)",
        "unknown": "확인 필요(UNKNOWN)",
    }
    return labels.get((value or "unknown").lower(), str(value or "unknown"))


def _source_label(value: str) -> str:
    labels = {
        "factory_state_snapshot": "공장 상태 스냅샷",
        "cloud_infra_fast": "클라우드 인프라 Fast 스냅샷",
        "cloud_infra_slow": "클라우드 인프라 Slow 스냅샷",
    }
    return labels.get(value, value)


def _section_lines(section: dict) -> list[str]:
    friendly_keys = {
        "name": "이름",
        "status": "상태",
        "errors_5m": "최근 5분 오류 수",
        "throttles_5m": "최근 5분 Throttle 수",
        "read_throttle_events_5m": "최근 5분 Read throttle",
        "write_throttle_events_5m": "최근 5분 Write throttle",
        "unhealthy_host_count": "비정상 호스트 수",
        "desired_capacity": "희망 인스턴스 수",
        "healthy_instances": "정상 인스턴스 수",
    }
    lines = []
    for key, value in section.items():
        label = friendly_keys.get(key, key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        lines.append(f"- {label}: {value}")
    return lines


def _webhook_url(alert: Alert) -> str:
    secret_id = _secret_id_for(alert)
    if secret_id:
        response = _boto3_client("secretsmanager").get_secret_value(SecretId=secret_id)
        value = response.get("SecretString") or ""
        try:
            decoded = json.loads(value)
            return decoded.get("url") or decoded.get("webhook_url") or value
        except json.JSONDecodeError:
            return value

    parameter_name = os.environ.get("SLACK_WEBHOOK_SSM_PARAMETER_NAME")
    if parameter_name:
        response = _boto3_client("ssm").get_parameter(Name=parameter_name, WithDecryption=True)
        return response["Parameter"]["Value"]

    raise SlackNotConfigured("SLACK_WEBHOOK_SECRET_ID or SLACK_WEBHOOK_SSM_PARAMETER_NAME is required")


def _secret_id_for(alert: Alert) -> str:
    env_by_scope = {
        "cloud-infra": "SLACK_WEBHOOK_SECRET_CLOUD",
        "factory-a": "SLACK_WEBHOOK_SECRET_FACTORY_A",
        "factory-b": "SLACK_WEBHOOK_SECRET_FACTORY_B",
        "factory-c": "SLACK_WEBHOOK_SECRET_FACTORY_C",
    }
    env_key = env_by_scope.get(alert.scope)
    if env_key and os.environ.get(env_key):
        return os.environ[env_key]
    return os.environ.get("SLACK_WEBHOOK_SECRET_ID", "")


def _boto3_client(service: str):
    import boto3

    return boto3.client(service)
