import os

from report_generator.time_window import prepare_report_window


def handler(event, context):
    timezone = event.get("timezone") or os.environ.get("REPORT_TIMEZONE", "Asia/Seoul")
    factories = event.get("factories") or _csv(os.environ.get("REPORT_FACTORY_IDS", "factory-a,factory-b,factory-c"))
    datasets = event.get("datasets") or _csv(os.environ.get("REPORT_DATASETS", "factory_state,risk_score,infra_state"))
    output_prefix_root = os.environ.get("REPORT_OUTPUT_PREFIX", "reports/daily")
    return prepare_report_window(
        report_date=event.get("report_date"),
        timezone_name=timezone,
        factories=factories,
        datasets=datasets,
        output_prefix_root=output_prefix_root,
    )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
