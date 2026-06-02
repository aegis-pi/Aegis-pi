import os

from report_generator.generate_cloud_infra_report import generate_cloud_infra_report
from report_generator.s3_reader import S3ProcessedReader
from report_generator.s3_writer import S3ReportWriter


def handler(event, context):
    bucket_name = os.environ.get("S3_BUCKET_NAME", "aegis-bucket-data")
    report_context = event.get("report_context")
    if report_context is None:
        report_context = S3ProcessedReader(bucket_name).read_json(event["context_key"])

    result = generate_cloud_infra_report(
        report_context=report_context,
        output_prefix=event["output_prefix"],
    )
    if result["status"] == "success":
        writer = S3ReportWriter(bucket_name)
        writer.write_text(result["report_key"], result["markdown"])
        writer.write_json(result["metadata_key"], result["generation_metadata"])
    return {
        key: value
        for key, value in result.items()
        if key not in ("markdown", "generation_metadata")
    }
