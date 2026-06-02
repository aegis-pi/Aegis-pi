from __future__ import annotations

import os
import time
from decimal import Decimal, InvalidOperation

import boto3
from botocore.exceptions import ClientError

from alert_dispatcher.rules import Alert


_dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "AEGIS-DynamoDB-FactoryStatus")
ALERT_TTL_SECONDS = int(os.environ.get("ALERT_STATE_TTL_SECONDS", str(7 * 24 * 3600)))
DEFAULT_COOLDOWNS = {
    ("factory_state_snapshot", "warning"): 15 * 60,
    ("factory_state_snapshot", "danger"): 5 * 60,
    ("cloud_infra_fast", "warning"): 15 * 60,
    ("cloud_infra_fast", "danger"): 5 * 60,
    ("cloud_infra_slow", "warning"): 15 * 60,
    ("cloud_infra_slow", "danger"): 5 * 60,
}


def reserve(alert: Alert, now_epoch: int | None = None) -> dict:
    now_epoch = now_epoch or int(time.time())
    cooldown_seconds = _cooldown_seconds(alert)
    cooldown_until = now_epoch + cooldown_seconds
    ttl = now_epoch + ALERT_TTL_SECONDS

    try:
        _table().update_item(
            Key={"pk": alert.pk, "sk": alert.sk},
            UpdateExpression=(
                "SET #scope = :scope, #source_type = :source_type, #severity = :severity,"
                " #reason = :reason, #status = :status, #last_sent_at = :now,"
                " #last_observed_at = :now, #cooldown_until = :cooldown_until,"
                " #last_score = :score, #last_source_key = :source_key,"
                " #last_source_updated_at = :source_updated_at,"
                " #last_slack_status = :pending, #ttl = :ttl"
            ),
            ConditionExpression=(
                "(attribute_not_exists(#last_source_updated_at) OR #last_source_updated_at < :source_updated_at)"
                " AND (attribute_not_exists(#cooldown_until) OR #cooldown_until <= :now)"
            ),
            ExpressionAttributeNames={
                "#scope": "scope",
                "#source_type": "source_type",
                "#severity": "severity",
                "#reason": "reason",
                "#status": "status",
                "#last_sent_at": "last_sent_at",
                "#last_observed_at": "last_observed_at",
                "#cooldown_until": "cooldown_until",
                "#last_score": "last_score",
                "#last_source_key": "last_source_key",
                "#last_source_updated_at": "last_source_updated_at",
                "#last_slack_status": "last_slack_status",
                "#ttl": "ttl",
            },
            ExpressionAttributeValues=_to_dynamo({
                ":scope": alert.scope,
                ":source_type": alert.source_type,
                ":severity": alert.severity,
                ":reason": alert.reason,
                ":status": alert.status,
                ":now": now_epoch,
                ":cooldown_until": cooldown_until,
                ":score": alert.score,
                ":source_key": alert.source_key,
                ":source_updated_at": alert.source_updated_at,
                ":pending": "pending",
                ":ttl": ttl,
            }),
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return {"reserved": False, "reason": "cooldown_or_stale_snapshot"}
        raise

    return {
        "reserved": True,
        "cooldown_until": cooldown_until,
        "ttl": ttl,
    }


def record_slack_result(alert: Alert, status: str, error: str | None = None):
    expression = "SET last_slack_status = :status, last_slack_error = :error"
    _table().update_item(
        Key={"pk": alert.pk, "sk": alert.sk},
        UpdateExpression=expression,
        ExpressionAttributeValues=_to_dynamo({
            ":status": status,
            ":error": error or "",
        }),
    )


def _cooldown_seconds(alert: Alert) -> int:
    env_key = f"COOLDOWN_{alert.source_type.upper()}_{alert.severity.upper()}_SECONDS"
    if os.environ.get(env_key):
        return int(os.environ[env_key])
    return DEFAULT_COOLDOWNS.get((alert.source_type, alert.severity), 15 * 60)


def _table():
    return _dynamodb.Table(TABLE_NAME)


def _to_dynamo(obj):
    if isinstance(obj, float):
        try:
            return Decimal(str(obj))
        except InvalidOperation:
            return Decimal("0")
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo(v) for v in obj]
    return obj
