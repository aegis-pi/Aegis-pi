import os
from decimal import Decimal, InvalidOperation

import boto3
from boto3.dynamodb.conditions import Key

from aggregator.bucket import format_utc, format_utc_millis


_dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "AEGIS-DynamoDB-FactoryStatus")
HISTORY_STATE_PREFIX = "HISTORY#STATE#"
GRAPH_5M_PREFIX = "GRAPH#5M#"


def _table():
    return _dynamodb.Table(TABLE_NAME)


def query_history(factory_id: str, bucket_start, bucket_end) -> list[dict]:
    pk = f"FACTORY#{factory_id}"
    start_sk = f"{HISTORY_STATE_PREFIX}{format_utc(bucket_start)}"
    end_sk = f"{HISTORY_STATE_PREFIX}{format_utc_millis(bucket_end)}"
    items = []
    kwargs = {
        "KeyConditionExpression": Key("pk").eq(pk) & Key("sk").between(start_sk, end_sk),
    }

    while True:
        response = _table().query(**kwargs)
        items.extend(_from_dynamo(response.get("Items", [])))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


def put_graph_item(item: dict):
    _table().put_item(Item=_to_dynamo(item))


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

