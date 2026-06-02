#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(APP_DIR))

from report_generator.aggregate_hour import aggregate_factory_hour_records
from report_generator.aggregate_cloud_infra_hour import aggregate_cloud_infra_hour_records
from report_generator.bedrock_client import MockBedrockReportClient
from report_generator.generate_report import generate_factory_report
from report_generator.generate_cloud_infra_report import generate_cloud_infra_report
from report_generator.merge_daily import merge_factory_daily
from report_generator.merge_cloud_infra_daily import merge_cloud_infra_daily
from report_generator.s3_keys import processed_prefix
from report_generator.time_window import prepare_report_window, parse_window_bound


DEFAULT_DATASETS = ("factory_state", "risk_score", "infra_state")
DEFAULT_AUX_DATASETS = ("state_snapshot",)


def main() -> int:
    args = parse_args()
    target = args.target or args.factory_id
    prepared = prepare_report_window(
        report_date=args.report_date,
        timezone_name=args.timezone,
        factories=[target] if target != "cloud-infra" else [],
        datasets=list(DEFAULT_DATASETS),
        output_prefix_root="reports/daily",
    )
    if target == "cloud-infra":
        return run_cloud_infra(args, prepared)
    args.factory_id = target
    output_dir = args.output_dir / f"{args.factory_id}-{args.report_date}"
    input_dir = output_dir / "input"
    hourly_dir = output_dir / "intermediate" / "hourly"
    output_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    hourly_dir.mkdir(parents=True, exist_ok=True)

    datasets = [*DEFAULT_DATASETS, *DEFAULT_AUX_DATASETS]
    print(
        f"Downloading S3 processed data: bucket={args.bucket} factory={args.factory_id} "
        f"date={args.report_date} timezone={args.timezone} workers={args.workers}",
        flush=True,
    )
    records_by_hour = download_or_load_records(
        bucket=args.bucket,
        factory_id=args.factory_id,
        hour_items=prepared["hour_items"],
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
        hour_window = prepared["hour_items"][hour]["hour_window"]
        summary = aggregate_factory_hour_records(
            factory_id=args.factory_id,
            report_date=args.report_date,
            timezone=args.timezone,
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
        timezone=args.timezone,
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

    client = MockBedrockReportClient(args.mock_bedrock_response) if args.mock_bedrock_response else None
    report_result = generate_factory_report(
        report_context=merged["report_context"],
        output_prefix=output_prefix,
        bedrock_client=client,
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
    parser.add_argument("--target", choices=["factory-a", "factory-b", "factory-c", "cloud-infra"], help="Report target. Defaults to --factory-id for backward compatibility.")
    parser.add_argument("--factory-id", default="factory-b")
    parser.add_argument("--report-date", default="2026-05-27", help="UTC date, YYYY-MM-DD.")
    parser.add_argument("--timezone", default="Asia/Seoul", help="Report window timezone.")
    parser.add_argument("--output-dir", type=Path, default=Path("/home/vicbear/Aegis/test_paper"))
    parser.add_argument("--model-id", default="anthropic.claude-3-sonnet-20240229-v1:0")
    parser.add_argument("--mock-bedrock-response", help="Use a fixed local Bedrock response instead of invoking Bedrock.")
    parser.add_argument("--max-context-events", type=int, default=10)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--refresh", action="store_true", help="Download from S3 even when local cache exists.")
    return parser.parse_args()


def run_cloud_infra(args: argparse.Namespace, prepared: dict) -> int:
    output_dir = args.output_dir / f"cloud-infra-{args.report_date}"
    input_dir = output_dir / "input"
    hourly_dir = output_dir / "intermediate" / "hourly"
    output_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    hourly_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Downloading S3 processed cloud infra data: bucket={args.bucket} "
        f"date={args.report_date} timezone={args.timezone} workers={args.workers}",
        flush=True,
    )
    records_by_hour = download_or_load_cloud_infra_records(
        bucket=args.bucket,
        hour_items=prepared["hour_items"],
        input_dir=input_dir,
        refresh=args.refresh,
        workers=args.workers,
    )
    output_prefix = (
        f"reports/daily/yyyy={args.report_date[0:4]}/"
        f"mm={args.report_date[5:7]}/dd={args.report_date[8:10]}/cloud-infra"
    )
    hourly_summaries = []
    for hour in range(24):
        hour_text = f"{hour:02d}"
        summary = aggregate_cloud_infra_hour_records(
            target_id="cloud-infra",
            report_date=args.report_date,
            timezone=args.timezone,
            hour=hour_text,
            hour_window=prepared["hour_items"][hour]["hour_window"],
            records_by_stream=records_by_hour[hour_text],
            output_prefix=output_prefix,
        )
        hourly_summaries.append(summary)
        write_json(hourly_dir / f"hh={hour_text}.json", summary)
        print(
            f"hh={hour_text} status={summary['status']} "
            f"fast={summary['data_quality'].get('fast_actual_count', 0)} "
            f"slow={summary['data_quality'].get('slow_actual_count', 0)} "
            f"max_gap_minutes={summary['data_quality'].get('max_gap_minutes', 0)}",
            flush=True,
        )

    merged = merge_cloud_infra_daily(
        target_id="cloud-infra",
        report_date=args.report_date,
        timezone=args.timezone,
        hourly_summaries=hourly_summaries,
        output_prefix=output_prefix,
        max_context_events=args.max_context_events,
    )
    daily_summary_path = output_dir / f"cloud-infra-{args.report_date}-daily-summary.json"
    context_path = output_dir / f"cloud-infra-{args.report_date}-report-context.json"
    write_json(daily_summary_path, merged["daily_summary"])
    write_json(context_path, merged["report_context"])
    print(
        "Cloud infra daily merge complete: "
        f"fast_rate={merged['daily_summary']['data_quality']['fast_collection_rate']} "
        f"slow_rate={merged['daily_summary']['data_quality']['slow_collection_rate']}",
        flush=True,
    )

    response = args.mock_bedrock_response or _default_cloud_infra_mock_response(args.report_date)
    client = MockBedrockReportClient(response)
    report_result = generate_cloud_infra_report(
        report_context=merged["report_context"],
        output_prefix=output_prefix,
        bedrock_client=client,
    )
    metadata_path = output_dir / f"cloud-infra-{args.report_date}-generation-metadata.json"
    if report_result["status"] != "success":
        write_json(metadata_path, report_result)
        print(f"Report generation failed: status={report_result['status']}", flush=True)
        for error in report_result.get("validation_errors", []):
            print(f"validation_error={error}", flush=True)
        return 2

    report_path = output_dir / f"cloud-infra-{args.report_date}-report.md"
    report_path.write_text(report_result["markdown"], encoding="utf-8")
    write_json(metadata_path, report_result["generation_metadata"])
    copy_text(report_path, args.output_dir / report_path.name)
    copy_json(daily_summary_path, args.output_dir / daily_summary_path.name)
    copy_json(context_path, args.output_dir / context_path.name)
    copy_json(metadata_path, args.output_dir / metadata_path.name)
    print(f"Report written: {report_path}", flush=True)
    print(f"Root copy written: {args.output_dir / report_path.name}", flush=True)
    return 0


def download_or_load_records(
    bucket: str,
    factory_id: str,
    hour_items: list[dict],
    datasets: list[str],
    input_dir: Path,
    refresh: bool,
    workers: int,
) -> dict[str, dict[str, list[dict]]]:
    s3 = make_s3_client()
    records_by_hour = {f"{hour:02d}": {dataset: [] for dataset in datasets} for hour in range(24)}
    for hour_item in hour_items:
        hour_text = hour_item["hour"]
        for dataset in datasets:
            records = []
            for prefix in processed_prefixes_for_hour_window(factory_id, dataset, hour_item["hour_window"]):
                cache_path = input_dir / prefix
                cache_path.mkdir(parents=True, exist_ok=True)
                if refresh or not any(cache_path.glob("*.json")):
                    clear_json_files(cache_path)
                    if isinstance(s3, AwsCliS3Client):
                        s3.sync_prefix(bucket, prefix, cache_path)
                        keys = list(cache_path.glob("*.json"))
                    else:
                        keys = list_s3_keys(s3, bucket, prefix)
                        download_keys(s3, bucket, keys, cache_path, workers)
                    print(f"downloaded dataset={dataset} hh={hour_text} prefix={prefix} objects={len(keys)}", flush=True)
                records.extend(read_json_records(cache_path))
            records_by_hour[hour_text][dataset] = records
    return records_by_hour


def download_or_load_cloud_infra_records(
    bucket: str,
    hour_items: list[dict],
    input_dir: Path,
    refresh: bool,
    workers: int,
) -> dict[str, dict[str, list[dict]]]:
    s3 = make_s3_client()
    records_by_hour = {f"{hour:02d}": {"fast": [], "slow": []} for hour in range(24)}
    for hour_item in hour_items:
        hour_text = hour_item["hour"]
        for stream in ("fast", "slow"):
            records = []
            for prefix in cloud_infra_prefixes_for_hour_window(stream, hour_item["hour_window"]):
                cache_path = input_dir / prefix
                cache_path.mkdir(parents=True, exist_ok=True)
                if refresh or not any(cache_path.glob("*.json")):
                    clear_json_files(cache_path)
                    if isinstance(s3, AwsCliS3Client):
                        s3.sync_prefix(bucket, prefix, cache_path)
                        keys = list(cache_path.glob("*.json"))
                    else:
                        keys = list_s3_keys(s3, bucket, prefix)
                        download_keys(s3, bucket, keys, cache_path, workers)
                    print(f"downloaded stream={stream} hh={hour_text} prefix={prefix} objects={len(keys)}", flush=True)
                records.extend(read_json_records(cache_path))
            records_by_hour[hour_text][stream] = records
    return records_by_hour


def processed_prefixes_for_hour_window(factory_id: str, dataset: str, hour_window: dict) -> list[str]:
    start = parse_window_bound(hour_window["start_utc"])
    end = parse_window_bound(hour_window["end_utc"])
    prefixes = []
    current = start.replace(minute=0, second=0, microsecond=0)
    last = end.replace(minute=0, second=0, microsecond=0)
    while current <= last:
        prefixes.append(processed_prefix(factory_id, dataset, current))
        current += timedelta(hours=1)
    return prefixes


def cloud_infra_prefixes_for_hour_window(stream: str, hour_window: dict) -> list[str]:
    start = parse_window_bound(hour_window["start_utc"])
    end = parse_window_bound(hour_window["end_utc"])
    prefixes = []
    current = start.replace(minute=0, second=0, microsecond=0)
    last = end.replace(minute=0, second=0, microsecond=0)
    while current <= last:
        prefixes.append(cloud_infra_processed_prefix(stream, current))
        current += timedelta(hours=1)
    return prefixes


def cloud_infra_processed_prefix(stream: str, dt: datetime) -> str:
    return (
        "processed/cloud_infra/"
        f"{stream}/yyyy={dt.year:04d}/mm={dt.month:02d}/"
        f"dd={dt.day:02d}/hh={dt.hour:02d}/"
    )


def list_s3_keys(s3, bucket: str, prefix: str) -> list[str]:
    if isinstance(s3, AwsCliS3Client):
        return s3.list_keys(bucket, prefix)
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
    if isinstance(s3, AwsCliS3Client):
        s3.download_key(bucket, key, local_path)
        return
    obj = s3.get_object(Bucket=bucket, Key=key)
    local_path.write_bytes(obj["Body"].read())


def make_s3_client():
    try:
        import boto3

        return boto3.client("s3")
    except ModuleNotFoundError:
        return AwsCliS3Client()


class AwsCliS3Client:
    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        result = subprocess.run(
            [
                "aws",
                "s3api",
                "list-objects-v2",
                "--bucket",
                bucket,
                "--prefix",
                prefix,
                "--query",
                "Contents[?ends_with(Key, `.json`)].Key",
                "--output",
                "json",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        return json.loads(result.stdout or "[]") or []

    def download_key(self, bucket: str, key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["aws", "s3", "cp", f"s3://{bucket}/{key}", str(local_path), "--only-show-errors"],
            check=True,
        )

    def sync_prefix(self, bucket: str, prefix: str, local_path: Path) -> None:
        local_path.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "aws",
                "s3",
                "sync",
                f"s3://{bucket}/{prefix}",
                str(local_path),
                "--exclude",
                "*",
                "--include",
                "*.json",
                "--only-show-errors",
            ],
            check=True,
        )


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


def _default_cloud_infra_mock_response(report_date: str) -> str:
    return "\n".join([
        f"# Cloud Infra 일일 운영 리포트 - {report_date}",
        "",
        "## 요약",
        "",
        f"cloud-infra {report_date} 리포트 초안입니다.",
        "",
        "## 데이터 수집 상태",
        "## Backend Runtime",
        "## Data Pipeline",
        "## EKS Management",
        "## ArgoCD 및 배포 상태",
        "## Factory Freshness 및 Storage Freshness",
        "## 주요 이벤트",
        "## 확인 필요 항목",
        "## 데이터 한계",
        "",
        "S3 processed 기반이며 LLM 초안은 운영자 검토가 필요합니다.",
    ])


if __name__ == "__main__":
    raise SystemExit(main())
