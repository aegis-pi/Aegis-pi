import logging
import os
from datetime import timedelta

from aggregator import bucket, dynamo, metrics, s3_writer


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    event = event or {}
    now = bucket.utc_now()
    bucket_minutes = int(event.get("bucket_minutes") or os.environ.get("BUCKET_MINUTES", "5"))
    factories = event.get("factories") or _factory_ids()
    write_dynamodb = bool(event.get("write_dynamodb", True))
    write_s3 = bool(event.get("write_s3", True))

    if event.get("bucket_start"):
        bucket_starts = [bucket.parse_utc(event["bucket_start"])]
    else:
        lookback_buckets = int(event.get("lookback_buckets") or os.environ.get("LOOKBACK_BUCKETS", "1"))
        bucket_starts = bucket.closed_buckets(now, bucket_minutes, lookback_buckets)

    results = []
    for factory_id in factories:
        for bucket_start in bucket_starts:
            bucket_end = bucket.bucket_end(bucket_start, bucket_minutes)
            source_items = dynamo.query_history(factory_id, bucket_start, bucket_end)
            graph_item = metrics.aggregate_graph_item(
                factory_id,
                bucket_start,
                bucket_end,
                source_items,
                created_at=now,
                graph_ttl_hours=int(os.environ.get("GRAPH_TTL_HOURS", "48")),
                expected_sample_interval_seconds=int(os.environ.get("EXPECTED_SAMPLE_INTERVAL_SECONDS", "3")),
                ai_score_threshold=float(os.environ.get("AI_SCORE_THRESHOLD", "0.7")),
            )

            if write_dynamodb:
                dynamo.put_graph_item(graph_item)
            s3_key = None
            if write_s3:
                s3_key = s3_writer.put_graph_object(graph_item, os.environ.get("S3_OUTPUT_PREFIX", "processed_agg"))

            result = {
                "factory_id": factory_id,
                "bucket_start": graph_item["bucket_start"],
                "source_count": graph_item["quality"]["source_count"],
                "dynamodb_sk": graph_item["sk"],
                "s3_key": s3_key,
            }
            results.append(result)
            logger.info(
                "graph bucket done: factory_id=%s bucket_start=%s source_count=%s",
                factory_id,
                graph_item["bucket_start"],
                graph_item["quality"]["source_count"],
            )

    return {
        "status": "ok",
        "bucket_minutes": bucket_minutes,
        "processed": results,
    }


def _factory_ids() -> list[str]:
    return [
        item.strip()
        for item in os.environ.get("FACTORY_IDS", "factory-a,factory-b,factory-c").split(",")
        if item.strip()
    ]

