import os

from report_generator.merge_cloud_infra_daily import merge_cloud_infra_daily
from report_generator.s3_reader import S3ProcessedReader
from report_generator.s3_writer import S3ReportWriter


def handler(event, context):
    bucket_name = os.environ.get("S3_BUCKET_NAME", "aegis-bucket-data")
    reader = S3ProcessedReader(bucket_name)
    hourly_summaries = event.get("hourly_summaries")
    if hourly_summaries is None:
        hourly_summaries = [
            reader.read_json(item["summary_key"])
            for item in event.get("hour_results", [])
            if item.get("summary_key")
        ]

    result = merge_cloud_infra_daily(
        target_id=event.get("target_id", "cloud-infra"),
        report_date=event["report_date"],
        timezone=event.get("timezone", "Asia/Seoul"),
        hourly_summaries=hourly_summaries,
        output_prefix=event["output_prefix"],
        max_context_events=int(os.environ.get("MAX_CONTEXT_EVENTS", "10")),
    )
    writer = S3ReportWriter(bucket_name)
    writer.write_json(result["daily_summary_key"], result["daily_summary"])
    writer.write_json(result["context_key"], result["report_context"])
    return {
        "target_id": result["target_id"],
        "report_date": result["report_date"],
        "status": result["status"],
        "daily_summary_key": result["daily_summary_key"],
        "context_key": result["context_key"],
        "output_prefix": event["output_prefix"],
    }
