import os

from report_generator.aggregate_cloud_infra_hour import aggregate_cloud_infra_hour_records
from report_generator.s3_reader import CloudInfraReader
from report_generator.s3_writer import S3ReportWriter


def handler(event, context):
    bucket_name = os.environ.get("S3_BUCKET_NAME", "aegis-bucket-data")
    records_by_stream = event.get("records_by_stream")
    if records_by_stream is None:
        records_by_stream = CloudInfraReader(bucket_name).read_hour(event["hour_window"])

    summary = aggregate_cloud_infra_hour_records(
        target_id=event.get("target_id", "cloud-infra"),
        report_date=event["report_date"],
        timezone=event.get("timezone", "Asia/Seoul"),
        hour=event["hour"],
        hour_window=event["hour_window"],
        records_by_stream=records_by_stream,
        output_prefix=event.get("output_prefix"),
    )
    if summary.get("summary_key"):
        S3ReportWriter(bucket_name).write_json(summary["summary_key"], summary)
    return {
        "target_id": summary["target_id"],
        "report_date": summary["report_date"],
        "hour": summary["hour"],
        "status": summary["status"],
        "summary_key": summary.get("summary_key"),
        "fast_actual_count": summary["data_quality"].get("fast_actual_count", 0),
        "slow_actual_count": summary["data_quality"].get("slow_actual_count", 0),
        "event_count": len(summary.get("events", [])),
    }
