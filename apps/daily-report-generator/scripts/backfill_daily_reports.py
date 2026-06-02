#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from inventory_daily_report_backfill import (  # noqa: E402
    ALL_TARGETS,
    build_inventory,
    make_s3_client,
    report_status,
)
from report_generator.aggregate_cloud_infra_hour import aggregate_cloud_infra_hour_records  # noqa: E402
from report_generator.aggregate_hour import aggregate_factory_hour_records  # noqa: E402
from report_generator.generate_cloud_infra_report import generate_cloud_infra_report  # noqa: E402
from report_generator.generate_report import generate_factory_report  # noqa: E402
from report_generator.merge_cloud_infra_daily import merge_cloud_infra_daily  # noqa: E402
from report_generator.merge_daily import merge_factory_daily  # noqa: E402
from report_generator.s3_reader import CloudInfraReader, S3ProcessedReader  # noqa: E402
from report_generator.s3_writer import S3ReportWriter  # noqa: E402
from report_generator.time_window import prepare_report_window  # noqa: E402


FACTORY_DATASETS = ("factory_state", "risk_score", "infra_state")
AUX_DATASETS = ("state_snapshot",)


def main() -> int:
    args = parse_args()
    if args.model_id:
        os.environ["BEDROCK_MODEL_ID"] = args.model_id
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    s3 = make_s3_client()
    if args.target_dates:
        inventory = build_target_date_inventory(
            s3=s3,
            bucket=args.bucket,
            target_dates=parse_target_dates(args.target_dates),
            timezone_name=args.timezone,
        )
    else:
        targets = parse_targets(args.targets)
        date_from = date.fromisoformat(args.date_from) if args.date_from else None
        date_to = date.fromisoformat(args.date_to) if args.date_to else None
        inventory = build_inventory(
            s3=s3,
            bucket=args.bucket,
            targets=targets,
            timezone_name=args.timezone,
            date_from=date_from,
            date_to=date_to,
        )
    items = select_items(inventory["items"], force=args.force, only_missing=args.only_missing)
    if args.max_bedrock_calls is not None:
        items = items[: args.max_bedrock_calls]

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "bucket": args.bucket,
        "timezone": args.timezone,
        "dry_run": args.dry_run,
        "force": args.force,
        "only_missing": args.only_missing,
        "max_bedrock_calls": args.max_bedrock_calls,
        "selected_count": len(items),
        "items": [],
    }
    if args.dry_run:
        for item in items:
            results["items"].append(result_stub(item, "would_generate"))
        write_results(output_dir, results)
        print_summary(output_dir, results)
        return 0

    reader = S3ProcessedReader(args.bucket)
    cloud_reader = CloudInfraReader(args.bucket)
    writer = S3ReportWriter(args.bucket)
    for item in items:
        if item["recommended_action"] == "force-needed" and not args.force:
            results["items"].append(result_stub(item, "skipped_force_needed"))
            continue
        try:
            if item["target"] == "cloud-infra":
                result = run_cloud_infra_item(item, args, cloud_reader, writer)
            else:
                result = run_factory_item(item, args, reader, writer)
            results["items"].append(result)
        except Exception as exc:  # noqa: BLE001
            failed = result_stub(item, "failed")
            failed["error"] = repr(exc)
            results["items"].append(failed)
        write_results(output_dir, results)

    write_results(output_dir, results)
    print_summary(output_dir, results)
    failed_count = sum(1 for item in results["items"] if item["status"] in ("failed", "validation_failed"))
    return 2 if failed_count else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill daily reports using existing report generator modules.")
    parser.add_argument("--bucket", default="aegis-bucket-data")
    parser.add_argument("--targets", default=",".join(ALL_TARGETS))
    parser.add_argument("--date-from", help="KST report_date lower bound, YYYY-MM-DD.")
    parser.add_argument("--date-to", help="KST report_date upper bound, YYYY-MM-DD.")
    parser.add_argument(
        "--target-dates",
        help="Comma-separated explicit backfill items, e.g. factory-a:2026-05-28,factory-b:2026-05-29.",
    )
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument("--only-missing", action="store_true", help="Skip complete reports.")
    parser.add_argument("--force", action="store_true", help="Regenerate selected reports even when outputs exist.")
    parser.add_argument("--max-bedrock-calls", type=int, help="Hard cap for report generation calls.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/aegis-reporting-backfill"))
    parser.add_argument("--model-id", default="anthropic.claude-3-sonnet-20240229-v1:0")
    parser.add_argument("--max-context-events", type=int, default=10)
    return parser.parse_args()


def parse_targets(value: str) -> list[str]:
    targets = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(targets) - set(ALL_TARGETS))
    if unknown:
        raise SystemExit(f"unknown targets: {', '.join(unknown)}")
    return targets


def parse_target_dates(value: str) -> list[tuple[str, str]]:
    items = []
    for raw_item in value.split(","):
        raw_item = raw_item.strip()
        if not raw_item:
            continue
        try:
            target, report_date = raw_item.split(":", 1)
        except ValueError as exc:
            raise SystemExit(f"invalid target date item: {raw_item}") from exc
        target = target.strip()
        report_date = report_date.strip()
        if target not in ALL_TARGETS:
            raise SystemExit(f"unknown target: {target}")
        date.fromisoformat(report_date)
        items.append((target, report_date))
    if not items:
        raise SystemExit("--target-dates did not contain any items")
    return items


def build_target_date_inventory(s3, bucket: str, target_dates: list[tuple[str, str]], timezone_name: str) -> dict:
    items = []
    for target, report_date in target_dates:
        item = build_target_date_item(s3, bucket, target, report_date, timezone_name)
        item.update(report_status(s3, bucket, target, report_date))
        item["recommended_action"] = recommend_action(item)
        items.append(item)
    return {"items": items}


def build_target_date_item(s3, bucket: str, target: str, report_date: str, timezone_name: str) -> dict:
    prepared = prepare_report_window(
        report_date=report_date,
        timezone_name=timezone_name,
        factories=[] if target == "cloud-infra" else [target],
        datasets=list(FACTORY_DATASETS),
        output_prefix_root="reports/daily",
    )
    output_prefix = (
        prepared["report_targets"][-1]["output_prefix"]
        if target == "cloud-infra"
        else prepared["factory_items"][0]["output_prefix"]
    )
    return {
        "target": target,
        "report_date": report_date,
        "output_prefix": output_prefix,
        "partial_day": None,
        "observed_kst_hour_count": None,
        "total_object_count": None,
    }


def recommend_action(item: dict) -> str:
    if item["already_has_report"]:
        return "skip"
    if item["has_report_md"] != item["has_generation_metadata"]:
        return "force-needed"
    return "generate"


def select_items(items: list[dict], force: bool, only_missing: bool) -> list[dict]:
    selected = []
    for item in sorted(items, key=lambda value: (value["report_date"], value["target"])):
        if force:
            selected.append(item)
        elif item["recommended_action"] == "generate":
            selected.append(item)
        elif item["recommended_action"] == "force-needed":
            selected.append(item)
        elif not only_missing:
            selected.append(result_to_skip(item))
    return [item for item in selected if item.get("_skip_status") is None]


def result_to_skip(item: dict) -> dict:
    skipped = dict(item)
    skipped["_skip_status"] = "skipped_complete"
    return skipped


def run_factory_item(item: dict, args: argparse.Namespace, reader: S3ProcessedReader, writer: S3ReportWriter) -> dict:
    target = item["target"]
    report_date = item["report_date"]
    prepared = prepare_report_window(
        report_date=report_date,
        timezone_name=args.timezone,
        factories=[target],
        datasets=list(FACTORY_DATASETS),
        output_prefix_root="reports/daily",
    )
    output_prefix = prepared["factory_items"][0]["output_prefix"]
    hourly_summaries = []
    for hour_item in prepared["hour_items"]:
        records_by_dataset = reader.read_hour(
            factory_id=target,
            datasets=[*FACTORY_DATASETS, *AUX_DATASETS],
            hour_window=hour_item["hour_window"],
        )
        summary = aggregate_factory_hour_records(
            factory_id=target,
            report_date=report_date,
            timezone=args.timezone,
            hour=hour_item["hour"],
            hour_window=hour_item["hour_window"],
            records_by_dataset=records_by_dataset,
            output_prefix=output_prefix,
        )
        hourly_summaries.append(summary)
        writer.write_json(summary["summary_key"], summary)

    merged = merge_factory_daily(
        factory_id=target,
        report_date=report_date,
        timezone=args.timezone,
        hourly_summaries=hourly_summaries,
        output_prefix=output_prefix,
        max_context_events=args.max_context_events,
    )
    writer.write_json(merged["daily_summary_key"], merged["daily_summary"])
    writer.write_json(merged["context_key"], merged["report_context"])
    report_result = generate_factory_report(merged["report_context"], output_prefix=output_prefix)
    return write_report_result(item, writer, merged, report_result)


def run_cloud_infra_item(item: dict, args: argparse.Namespace, reader: CloudInfraReader, writer: S3ReportWriter) -> dict:
    report_date = item["report_date"]
    prepared = prepare_report_window(
        report_date=report_date,
        timezone_name=args.timezone,
        factories=[],
        datasets=list(FACTORY_DATASETS),
        output_prefix_root="reports/daily",
    )
    output_prefix = f"{prepared['output_prefix']}/cloud-infra"
    hourly_summaries = []
    for hour_item in prepared["hour_items"]:
        records_by_stream = reader.read_hour(hour_item["hour_window"])
        summary = aggregate_cloud_infra_hour_records(
            target_id="cloud-infra",
            report_date=report_date,
            timezone=args.timezone,
            hour=hour_item["hour"],
            hour_window=hour_item["hour_window"],
            records_by_stream=records_by_stream,
            output_prefix=output_prefix,
        )
        hourly_summaries.append(summary)
        writer.write_json(summary["summary_key"], summary)

    merged = merge_cloud_infra_daily(
        target_id="cloud-infra",
        report_date=report_date,
        timezone=args.timezone,
        hourly_summaries=hourly_summaries,
        output_prefix=output_prefix,
        max_context_events=args.max_context_events,
    )
    writer.write_json(merged["daily_summary_key"], merged["daily_summary"])
    writer.write_json(merged["context_key"], merged["report_context"])
    report_result = generate_cloud_infra_report(merged["report_context"], output_prefix=output_prefix)
    return write_report_result(item, writer, merged, report_result)


def write_report_result(item: dict, writer: S3ReportWriter, merged: dict, report_result: dict) -> dict:
    result = result_stub(item, report_result["status"])
    result["daily_summary_key"] = merged["daily_summary_key"]
    result["context_key"] = merged["context_key"]
    if report_result["status"] != "success":
        result["validation_errors"] = report_result.get("validation_errors", [])
        return result
    writer.write_text(report_result["report_key"], report_result["markdown"])
    writer.write_json(report_result["metadata_key"], report_result["generation_metadata"])
    result["report_key"] = report_result["report_key"]
    result["metadata_key"] = report_result["metadata_key"]
    result["model_id"] = report_result["generation_metadata"].get("model_id")
    return result


def result_stub(item: dict, status: str) -> dict:
    return {
        "target": item["target"],
        "report_date": item["report_date"],
        "status": status,
        "output_prefix": item["output_prefix"],
        "partial_day": item["partial_day"],
        "observed_kst_hour_count": item["observed_kst_hour_count"],
        "total_object_count": item["total_object_count"],
    }


def write_results(output_dir: Path, results: dict) -> None:
    json_path = output_dir / "backfill-results.json"
    markdown_path = output_dir / "backfill-results.md"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_results_markdown(results), encoding="utf-8")


def render_results_markdown(results: dict) -> str:
    lines = [
        "# Daily Report Backfill Results",
        "",
        f"- generated_at: {results['generated_at']}",
        f"- bucket: {results['bucket']}",
        f"- dry_run: {str(results['dry_run']).lower()}",
        f"- selected_count: {results['selected_count']}",
        "",
        "| target | report_date | status | partial | kst_hours | objects |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for item in results["items"]:
        lines.append(
            f"| {item['target']} | {item['report_date']} | {item['status']} | "
            f"{str(item['partial_day']).lower()} | {item['observed_kst_hour_count']} | "
            f"{item['total_object_count']} |"
        )
    failures = [item for item in results["items"] if item["status"] in ("failed", "validation_failed")]
    if failures:
        lines.extend(["", "## Failures", ""])
        for item in failures:
            lines.append(f"- {item['target']} {item['report_date']}: {item.get('error') or item.get('validation_errors')}")
    return "\n".join(lines) + "\n"


def print_summary(output_dir: Path, results: dict) -> None:
    status_counts: dict[str, int] = {}
    for item in results["items"]:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    print(f"results_json={output_dir / 'backfill-results.json'}")
    print(f"results_markdown={output_dir / 'backfill-results.md'}")
    print(f"status_counts={json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}")


if __name__ == "__main__":
    raise SystemExit(main())
