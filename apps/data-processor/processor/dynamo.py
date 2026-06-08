import os
import time
from decimal import Decimal, InvalidOperation

import boto3

_dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "aegis-factory-status")
HISTORY_TTL_SECONDS = int(os.environ.get("HISTORY_TTL_HOURS", "2")) * 3600
LATEST_SK = "LATEST"
HISTORY_STATE_PREFIX = "HISTORY#STATE#"
RISK_CALCULATION_VERSION = "risk-v0.2.0"


def _table():
    return _dynamodb.Table(TABLE_NAME)


def get_last_infra_state_at(factory_id: str) -> str | None:
    item = _get_latest_state(factory_id)
    return item.get("last_infra_state_at") if item else None


def get_latest_state(factory_id: str) -> dict:
    return _from_dynamo(_get_latest_state(factory_id))


def write_factory_state_snapshot(
    factory_id: str,
    envelope: dict,
    normalized: dict,
    risk: dict,
    pipeline_status: dict,
    now_iso: str,
):
    _table().update_item(
        Key={"pk": f"FACTORY#{factory_id}", "sk": LATEST_SK},
        UpdateExpression=(
            "SET factory_state = :fs, #r = :r, pipeline_status = :ps,"
            " last_factory_state_at = :t, updated_at = :u,"
            " factory_id = :fid, schema_version = :sv"
        ),
        ExpressionAttributeNames={"#r": "risk"},
        ExpressionAttributeValues={
            ":fs": _to_dynamo(_state_payload(envelope, normalized)),
            ":r": _to_dynamo({
                **risk,
                "calculated_at": now_iso,
                "calculation_version": RISK_CALCULATION_VERSION,
            }),
            ":ps": _to_dynamo(pipeline_status),
            ":t": envelope["source_timestamp"],
            ":u": now_iso,
            ":fid": factory_id,
            ":sv": envelope["schema_version"],
        },
    )
    return _write_history_from_latest(factory_id, now_iso)


def write_infra_state_snapshot(
    factory_id: str,
    envelope: dict,
    normalized: dict,
    pipeline_status: dict,
    now_iso: str,
    risk: dict | None = None,
):
    expression = (
        "SET infra_state = :is, pipeline_status = :ps,"
        " last_infra_state_at = :t, updated_at = :u,"
        " factory_id = :fid, schema_version = :sv"
    )
    values = {
        ":is": _to_dynamo(_state_payload(envelope, normalized)),
        ":ps": _to_dynamo(pipeline_status),
        ":t": envelope["source_timestamp"],
        ":u": now_iso,
        ":fid": factory_id,
        ":sv": envelope["schema_version"],
    }
    names = None
    if risk:
        expression += ", #r = :r"
        values[":r"] = _to_dynamo({
            **risk,
            "calculated_at": now_iso,
            "calculation_version": RISK_CALCULATION_VERSION,
        })
        names = {"#r": "risk"}

    kwargs = {
        "Key": {"pk": f"FACTORY#{factory_id}", "sk": LATEST_SK},
        "UpdateExpression": expression,
        "ExpressionAttributeValues": values,
    }
    if names:
        kwargs["ExpressionAttributeNames"] = names
    _table().update_item(**kwargs)
    return _write_history_from_latest(factory_id, now_iso)


def write_pipeline_status_snapshot(
    factory_id: str,
    pipeline_status: dict,
    now_iso: str,
    risk: dict | None = None,
):
    expression = "SET pipeline_status = :ps, updated_at = :u"
    values = {
        ":ps": _to_dynamo(pipeline_status),
        ":u": now_iso,
    }
    names = None
    if risk:
        expression += ", #r = :r"
        values[":r"] = _to_dynamo({
            **risk,
            "calculated_at": now_iso,
            "calculation_version": RISK_CALCULATION_VERSION,
        })
        names = {"#r": "risk"}

    kwargs = {
        "Key": {"pk": f"FACTORY#{factory_id}", "sk": LATEST_SK},
        "UpdateExpression": expression,
        "ExpressionAttributeValues": values,
    }
    if names:
        kwargs["ExpressionAttributeNames"] = names
    _table().update_item(**kwargs)
    return _write_history_from_latest(factory_id, now_iso)


def write_image_snapshot_reference(
    factory_id: str,
    envelope: dict,
    normalized: dict,
    now_iso: str,
):
    latest_image_snapshot = {
        "event_type": normalized["event_type"],
        "source_timestamp": envelope["source_timestamp"],
        "processed_at": now_iso,
        "s3_bucket": normalized["s3_bucket"],
        "s3_key": normalized["s3_key"],
        "content_type": normalized["content_type"],
        "size_bytes": normalized["size_bytes"],
        "sha256": normalized["sha256"],
        "message_id": envelope["message_id"],
    }
    _table().update_item(
        Key={"pk": f"FACTORY#{factory_id}", "sk": LATEST_SK},
        UpdateExpression=(
            "SET latest_image_snapshot = :lis,"
            " last_image_snapshot_at = :t, updated_at = :u,"
            " factory_id = :fid, schema_version = :sv"
        ),
        ExpressionAttributeValues={
            ":lis": _to_dynamo(latest_image_snapshot),
            ":t": envelope["source_timestamp"],
            ":u": now_iso,
            ":fid": factory_id,
            ":sv": envelope["schema_version"],
        },
    )
    return _write_history_from_latest(factory_id, now_iso)


def _get_latest_state(factory_id: str) -> dict:
    resp = _table().get_item(Key={"pk": f"FACTORY#{factory_id}", "sk": LATEST_SK})
    return resp.get("Item", {})


def _state_payload(envelope: dict, normalized: dict) -> dict:
    return {
        **normalized,
        "message_id": envelope["message_id"],
        "source_timestamp": envelope["source_timestamp"],
    }


def _write_history_from_latest(factory_id: str, now_iso: str):
    history = _get_latest_state(factory_id)
    if not history:
        return None
    history["sk"] = f"{HISTORY_STATE_PREFIX}{now_iso}"
    history["ttl"] = int(time.time()) + HISTORY_TTL_SECONDS
    _table().put_item(Item=_to_dynamo(history))
    s3_snapshot = dict(history)
    s3_snapshot.pop("ttl", None)
    return _from_dynamo(s3_snapshot)


def _to_dynamo(obj):
    """Recursively convert floats to Decimal; boto3 DynamoDB resource rejects float."""
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


def _from_dynamo(obj):
    if isinstance(obj, Decimal):
        if obj == obj.to_integral_value():
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_dynamo(v) for v in obj]
    return obj
