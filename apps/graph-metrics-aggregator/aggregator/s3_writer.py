import json
import os

import boto3

from aggregator.bucket import parse_utc, s3_metrics_5m_key


_s3 = boto3.client("s3")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "aegis-bucket-data")


def graph_object_body(graph_item: dict) -> dict:
    body = dict(graph_item)
    body.pop("pk", None)
    body.pop("sk", None)
    body.pop("ttl", None)
    body["dynamodb_pk"] = graph_item["pk"]
    body["dynamodb_sk"] = graph_item["sk"]
    return body


def put_graph_object(graph_item: dict, prefix: str = "processed_agg") -> str:
    key = s3_metrics_5m_key(prefix, graph_item["factory_id"], parse_utc(graph_item["bucket_start"]))
    _s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(graph_object_body(graph_item), ensure_ascii=False, default=str),
        ContentType="application/json",
    )
    return key

