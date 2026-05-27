import os

from report_generator.aggregate_hour import aggregate_factory_hour_records
from report_generator.s3_reader import S3ProcessedReader
from report_generator.s3_writer import S3ReportWriter


def handler(event, context):
    records_by_dataset = event.get("records_by_dataset")
    bucket_name = os.environ.get("S3_BUCKET_NAME", "aegis-bucket-data")
    datasets = event.get("datasets", ["factory_state", "risk_score", "infra_state"])
    auxiliary_datasets = event.get("auxiliary_datasets", _csv(os.environ.get("REPORT_AUX_DATASETS", "state_snapshot")))
    if records_by_dataset is None:
        records_by_dataset = S3ProcessedReader(bucket_name).read_hour(
            factory_id=event["factory_id"],
            datasets=[*datasets, *auxiliary_datasets],
            hour_window=event["hour_window"],
        )

    summary = aggregate_factory_hour_records(
        factory_id=event["factory_id"],
        report_date=event["report_date"],
        timezone=event.get("timezone", "Asia/Seoul"),
        hour=event["hour"],
        hour_window=event["hour_window"],
        records_by_dataset=records_by_dataset,
        output_prefix=event.get("output_prefix"),
    )
    if summary.get("summary_key"):
        S3ReportWriter(bucket_name).write_json(summary["summary_key"], summary)
    return {
        "factory_id": summary["factory_id"],
        "report_date": summary["report_date"],
        "hour": summary["hour"],
        "status": summary["status"],
        "summary_key": summary.get("summary_key"),
        "input_counts": {
            dataset: summary["input_counts"].get(dataset, 0)
            for dataset in [*datasets, *auxiliary_datasets]
        },
        "event_count": len(summary.get("events", [])),
    }


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
