#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(APP_DIR))

from report_generator.aggregate_hour import aggregate_factory_hour_records
from report_generator.generate_report import generate_factory_report
from report_generator.merge_daily import merge_factory_daily
from report_generator.s3_keys import processed_prefix


DEFAULT_DATASETS = ("factory_state", "risk_score", "infra_state")
DEFAULT_AUX_DATASETS = ("state_snapshot",)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir / f"{args.factory_id}-{args.report_date}"
    input_dir = output_dir / "input"
    hourly_dir = output_dir / "intermediate" / "hourly"
    output_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    hourly_dir.mkdir(parents=True, exist_ok=True)

    datasets = [*DEFAULT_DATASETS, *DEFAULT_AUX_DATASETS]
    print(
        f"Downloading S3 processed data: bucket={args.bucket} factory={args.factory_id} "
        f"date={args.report_date} timezone=UTC workers={args.workers}",
        flush=True,
    )
    records_by_hour = download_or_load_records(
        bucket=args.bucket,
        factory_id=args.factory_id,
        report_date=args.report_date,
        datasets=datasets,
        input_dir=input_dir,
        refresh=args.refresh,
        workers=args.workers,
    )

    output_prefix = (
        f"reports/daily/yyyy={args.report_date[0:4]}/"
        f"mm={args.report_date[5:7]}/dd={args.report_date[8:10]}/{args.factory_id}"
    )
    hourly_summaries = []
    for hour in range(24):
        hour_text = f"{hour:02d}"
        hour_window = utc_hour_window(args.report_date, hour)
        summary = aggregate_factory_hour_records(
            factory_id=args.factory_id,
            report_date=args.report_date,
            timezone="UTC",
            hour=hour_text,
            hour_window=hour_window,
            records_by_dataset=records_by_hour[hour_text],
            output_prefix=output_prefix,
        )
        hourly_summaries.append(summary)
        write_json(hourly_dir / f"hh={hour_text}.json", summary)
        counts = summary["input_counts"]
        print(
            f"hh={hour_text} status={summary['status']} "
            f"factory_state={counts.get('factory_state', 0)} "
            f"risk_score={counts.get('risk_score', 0)} "
            f"infra_state={counts.get('infra_state', 0)} "
            f"state_snapshot={counts.get('state_snapshot', 0)} "
            f"max_gap_seconds={summary['data_quality'].get('max_gap_seconds', 0)}",
            flush=True,
        )

    merged = merge_factory_daily(
        factory_id=args.factory_id,
        report_date=args.report_date,
        timezone="UTC",
        hourly_summaries=hourly_summaries,
        output_prefix=output_prefix,
        max_context_events=args.max_context_events,
    )
    daily_summary_path = output_dir / f"{args.factory_id}-{args.report_date}-daily-summary.json"
    context_path = output_dir / f"{args.factory_id}-{args.report_date}-report-context.json"
    write_json(daily_summary_path, merged["daily_summary"])
    write_json(context_path, merged["report_context"])

    print(
        "Daily merge complete: "
        f"missing_hour_count={merged['daily_summary']['data_quality']['missing_hour_count']} "
        f"max_gap_minutes={merged['daily_summary']['data_quality']['max_gap_minutes']}",
        flush=True,
    )
    print(f"Invoking Bedrock model: {args.model_id}", flush=True)
    if args.model_id:
        import os

        os.environ["BEDROCK_MODEL_ID"] = args.model_id

    report_result = generate_factory_report(
        report_context=merged["report_context"],
        output_prefix=output_prefix,
    )
    metadata_path = output_dir / f"{args.factory_id}-{args.report_date}-generation-metadata.json"
    if report_result["status"] != "success":
        write_json(metadata_path, report_result)
        print(f"Report generation failed: status={report_result['status']}", flush=True)
        for error in report_result.get("validation_errors", []):
            print(f"validation_error={error}", flush=True)
        return 2

    report_path = output_dir / f"{args.factory_id}-{args.report_date}-report.md"
    report_path.write_text(report_result["markdown"], encoding="utf-8")
    write_json(metadata_path, report_result["generation_metadata"])

    # Convenience copies at the requested root path.
    copy_text(report_path, args.output_dir / report_path.name)
    copy_json(daily_summary_path, args.output_dir / daily_summary_path.name)
    copy_json(context_path, args.output_dir / context_path.name)
    copy_json(metadata_path, args.output_dir / metadata_path.name)

    print(f"Report written: {report_path}", flush=True)
    print(f"Root copy written: {args.output_dir / report_path.name}", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local daily factory report pipeline against S3 processed data.")
    parser.add_argument("--bucket", default="aegis-bucket-data")
    parser.add_argument("--factory-id", default="factory-b")
    parser.add_argument("--report-date", default="2026-05-27", help="UTC date, YYYY-MM-DD.")
    parser.add_argument("--output-dir", type=Path, default=Path("/home/vicbear/Aegis/test_paper"))
    parser.add_argument("--model-id", default="anthropic.claude-3-sonnet-20240229-v1:0")
    parser.add_argument("--max-context-events", type=int, default=10)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--refresh", action="store_true", help="Download from S3 even when local cache exists.")
    return parser.parse_args()


def download_or_load_records(
    bucket: str,
    factory_id: str,
    report_date: str,
    datasets: list[str],
    input_dir: Path,
    refresh: bool,
    workers: int,
) -> dict[str, dict[str, list[dict]]]:
    import boto3

    s3 = boto3.client("s3")
    records_by_hour = {f"{hour:02d}": {dataset: [] for dataset in datasets} for hour in range(24)}
    for hour in range(24):
        hour_text = f"{hour:02d}"
        dt = datetime.fromisoformat(f"{report_date}T{hour_text}:00:00+00:00")
        for dataset in datasets:
            prefix = processed_prefix(factory_id, dataset, dt)
            cache_path = input_dir / prefix
            cache_path.mkdir(parents=True, exist_ok=True)
            if refresh or not any(cache_path.glob("*.json")):
                clear_json_files(cache_path)
                keys = list_s3_keys(s3, bucket, prefix)
                download_keys(s3, bucket, keys, cache_path, workers)
                print(f"downloaded dataset={dataset} hh={hour_text} objects={len(keys)}", flush=True)
            records_by_hour[hour_text][dataset] = read_json_records(cache_path)
    return records_by_hour


def list_s3_keys(s3, bucket: str, prefix: str) -> list[str]:
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(item["Key"] for item in page.get("Contents", []) if item["Key"].endswith(".json"))
    return keys


def download_keys(s3, bucket: str, keys: list[str], cache_path: Path, workers: int) -> None:
    if not keys:
        return
    with ThreadPoolExecutor(max_workers=max(workers, 1)) as executor:
        futures = [
            executor.submit(download_one_key, s3, bucket, key, cache_path / Path(key).name)
            for key in keys
        ]
        for future in as_completed(futures):
            future.result()


def download_one_key(s3, bucket: str, key: str, local_path: Path) -> None:
    obj = s3.get_object(Bucket=bucket, Key=key)
    local_path.write_bytes(obj["Body"].read())


def read_json_records(path: Path) -> list[dict]:
    records = []
    for json_path in sorted(path.glob("*.json")):
        records.append(json.loads(json_path.read_text(encoding="utf-8")))
    return records


def clear_json_files(path: Path) -> None:
    for json_path in path.glob("*.json"):
        json_path.unlink()


def utc_hour_window(report_date: str, hour: int) -> dict:
    start = datetime.fromisoformat(f"{report_date}T{hour:02d}:00:00+00:00")
    end = start + timedelta(hours=1) - timedelta(seconds=1)
    return {
        "start_kst": iso_z(start),
        "end_kst": iso_z(end),
        "start_utc": iso_z(start),
        "end_utc": iso_z(end),
    }


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def copy_text(source: Path, target: Path) -> None:
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def copy_json(source: Path, target: Path) -> None:
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
