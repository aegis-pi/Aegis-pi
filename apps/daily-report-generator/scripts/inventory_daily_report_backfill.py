#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


FACTORY_TARGETS = ("factory-a", "factory-b", "factory-c")
ALL_TARGETS = (*FACTORY_TARGETS, "cloud-infra")
FACTORY_DATASETS = ("factory_state", "risk_score", "infra_state", "state_snapshot")
CLOUD_INFRA_STREAMS = ("fast", "slow")
PARTITION_RE = re.compile(
    r"yyyy=(?P<year>\d{4})/mm=(?P<month>\d{2})/dd=(?P<day>\d{2})/hh=(?P<hour>\d{2})/"
)


def main() -> int:
    args = parse_args()
    targets = parse_targets(args.targets)
    date_from = date.fromisoformat(args.date_from) if args.date_from else None
    date_to = date.fromisoformat(args.date_to) if args.date_to else None
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    s3 = make_s3_client()
    inventory = build_inventory(
        s3=s3,
        bucket=args.bucket,
        targets=targets,
        timezone_name=args.timezone,
        date_from=date_from,
        date_to=date_to,
    )
    inventory["summary"] = summarize_inventory(inventory["items"])
    inventory_path = output_dir / "inventory.json"
    markdown_path = output_dir / "inventory.md"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(inventory), encoding="utf-8")

    summary = inventory["summary"]
    print(f"inventory_json={inventory_path}")
    print(f"inventory_markdown={markdown_path}")
    print(
        "summary "
        f"candidate_items={summary['candidate_items']} "
        f"already_complete={summary['already_complete']} "
        f"missing_reports={summary['missing_reports']} "
        f"partial_items={summary['partial_items']} "
        f"estimated_bedrock_calls_only_missing={summary['estimated_bedrock_calls_only_missing']} "
        f"estimated_bedrock_calls_force={summary['estimated_bedrock_calls_force']}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a read-only S3 inventory for daily report backfill.")
    parser.add_argument("--bucket", default="aegis-bucket-data")
    parser.add_argument("--targets", default=",".join(ALL_TARGETS))
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument("--date-from", help="KST report_date lower bound, YYYY-MM-DD.")
    parser.add_argument("--date-to", help="KST report_date upper bound, YYYY-MM-DD.")
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/aegis-reporting-backfill"))
    return parser.parse_args()


def parse_targets(value: str) -> list[str]:
    targets = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(targets) - set(ALL_TARGETS))
    if unknown:
        raise SystemExit(f"unknown targets: {', '.join(unknown)}")
    return targets


def build_inventory(
    s3,
    bucket: str,
    targets: list[str],
    timezone_name: str,
    date_from: date | None,
    date_to: date | None,
) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    items = []
    for target in targets:
        if target == "cloud-infra":
            counts = collect_partition_counts(s3, bucket, "processed/cloud_infra", CLOUD_INFRA_STREAMS)
        else:
            counts = collect_partition_counts(s3, bucket, f"processed/{target}", FACTORY_DATASETS)
        for report_date, item in sorted(group_target_counts(target, counts, timezone_name).items()):
            report_date_value = date.fromisoformat(report_date)
            if date_from and report_date_value < date_from:
                continue
            if date_to and report_date_value > date_to:
                continue
            item.update(report_status(s3, bucket, target, report_date))
            item["recommended_action"] = recommend_action(item)
            items.append(item)
    return {
        "generated_at": generated_at,
        "bucket": bucket,
        "timezone": timezone_name,
        "targets": targets,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "items": items,
    }


def collect_partition_counts(s3, bucket: str, root_prefix: str, sources: tuple[str, ...]) -> dict:
    counts: dict[str, dict[str, int]] = {source: defaultdict(int) for source in sources}
    for source in sources:
        prefix = f"{root_prefix}/{source}/"
        for key in list_keys(s3, bucket, prefix):
            match = PARTITION_RE.search(key)
            if not match:
                continue
            utc_hour = (
                f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
                f"T{match.group('hour')}:00:00Z"
            )
            counts[source][utc_hour] += 1
    return counts


def group_target_counts(target: str, counts: dict, timezone_name: str) -> dict[str, dict]:
    tz = ZoneInfo(timezone_name)
    grouped: dict[str, dict] = {}
    for source, hour_counts in counts.items():
        for utc_hour, count in hour_counts.items():
            utc_dt = datetime.strptime(utc_hour, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            kst_dt = utc_dt.astimezone(tz)
            report_date = kst_dt.date().isoformat()
            item = grouped.setdefault(report_date, new_item(target, report_date))
            item["observed_utc_hours"].add(utc_hour)
            item["observed_kst_hours"].add(kst_dt.strftime("%Y-%m-%dT%H:00:00%z"))
            item["counts_by_source"].setdefault(source, {})[utc_hour] = count
            item["total_object_count"] += count
    for item in grouped.values():
        item["observed_utc_hours"] = sorted(item["observed_utc_hours"])
        item["observed_kst_hours"] = sorted(item["observed_kst_hours"])
        item["observed_kst_hour_count"] = len(item["observed_kst_hours"])
        item["partial_day"] = item["observed_kst_hour_count"] < 24
        item["counts_by_source"] = {
            source: {
                "total": sum(hour_counts.values()),
                "hours": dict(sorted(hour_counts.items())),
            }
            for source, hour_counts in sorted(item["counts_by_source"].items())
        }
    return grouped


def new_item(target: str, report_date: str) -> dict:
    return {
        "target": target,
        "report_date": report_date,
        "observed_utc_hours": set(),
        "observed_kst_hours": set(),
        "observed_kst_hour_count": 0,
        "partial_day": True,
        "counts_by_source": {},
        "total_object_count": 0,
    }


def report_status(s3, bucket: str, target: str, report_date: str) -> dict:
    prefix = report_prefix(target, report_date)
    report_key = f"{prefix}/report.md"
    metadata_key = f"{prefix}/generation-metadata.json"
    has_report = object_exists(s3, bucket, report_key)
    has_metadata = object_exists(s3, bucket, metadata_key)
    return {
        "output_prefix": prefix,
        "report_key": report_key,
        "metadata_key": metadata_key,
        "has_report_md": has_report,
        "has_generation_metadata": has_metadata,
        "already_has_report": has_report and has_metadata,
    }


def recommend_action(item: dict) -> str:
    if item["already_has_report"]:
        return "skip"
    if item["has_report_md"] != item["has_generation_metadata"]:
        return "force-needed"
    return "generate"


def report_prefix(target: str, report_date: str) -> str:
    return (
        f"reports/daily/yyyy={report_date[0:4]}/"
        f"mm={report_date[5:7]}/dd={report_date[8:10]}/{target}"
    )


def summarize_inventory(items: list[dict]) -> dict:
    missing = [item for item in items if item["recommended_action"] in ("generate", "force-needed")]
    return {
        "candidate_items": len(items),
        "already_complete": sum(1 for item in items if item["recommended_action"] == "skip"),
        "missing_reports": len(missing),
        "partial_items": sum(1 for item in items if item["partial_day"]),
        "estimated_bedrock_calls_only_missing": len(missing),
        "estimated_bedrock_calls_force": len(items),
        "by_target": {
            target: {
                "candidate_items": sum(1 for item in items if item["target"] == target),
                "missing_reports": sum(
                    1
                    for item in items
                    if item["target"] == target and item["recommended_action"] in ("generate", "force-needed")
                ),
                "already_complete": sum(
                    1 for item in items if item["target"] == target and item["recommended_action"] == "skip"
                ),
            }
            for target in ALL_TARGETS
            if any(item["target"] == target for item in items)
        },
    }


def render_markdown(inventory: dict) -> str:
    summary = inventory["summary"]
    lines = [
        "# Daily Report Backfill Inventory",
        "",
        f"- generated_at: {inventory['generated_at']}",
        f"- bucket: {inventory['bucket']}",
        f"- timezone: {inventory['timezone']}",
        f"- targets: {', '.join(inventory['targets'])}",
        f"- date_from: {inventory['date_from'] or '(none)'}",
        f"- date_to: {inventory['date_to'] or '(none)'}",
        "",
        "## Summary",
        "",
        f"- candidate_items: {summary['candidate_items']}",
        f"- already_complete: {summary['already_complete']}",
        f"- missing_reports: {summary['missing_reports']}",
        f"- partial_items: {summary['partial_items']}",
        f"- estimated_bedrock_calls_only_missing: {summary['estimated_bedrock_calls_only_missing']}",
        f"- estimated_bedrock_calls_force: {summary['estimated_bedrock_calls_force']}",
        "",
        "## By Target",
        "",
        "| target | candidates | missing | already_complete |",
        "| --- | ---: | ---: | ---: |",
    ]
    for target, values in summary["by_target"].items():
        lines.append(
            f"| {target} | {values['candidate_items']} | "
            f"{values['missing_reports']} | {values['already_complete']} |"
        )
    lines.extend([
        "",
        "## Items",
        "",
        "| target | report_date | action | partial | kst_hours | objects | report | metadata |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for item in inventory["items"]:
        lines.append(
            f"| {item['target']} | {item['report_date']} | {item['recommended_action']} | "
            f"{str(item['partial_day']).lower()} | {item['observed_kst_hour_count']} | "
            f"{item['total_object_count']} | {str(item['has_report_md']).lower()} | "
            f"{str(item['has_generation_metadata']).lower()} |"
        )
    return "\n".join(lines) + "\n"


def make_s3_client():
    try:
        import boto3

        return boto3.client("s3")
    except ModuleNotFoundError:
        return AwsCliS3Client()


def list_keys(s3, bucket: str, prefix: str) -> list[str]:
    if isinstance(s3, AwsCliS3Client):
        return s3.list_keys(bucket, prefix)
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(item["Key"] for item in page.get("Contents", []))
    return keys


def object_exists(s3, bucket: str, key: str) -> bool:
    if isinstance(s3, AwsCliS3Client):
        return s3.object_exists(bucket, key)
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


class AwsCliS3Client:
    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        keys = []
        token = None
        while True:
            command = [
                "aws",
                "s3api",
                "list-objects-v2",
                "--bucket",
                bucket,
                "--prefix",
                prefix,
                "--output",
                "json",
            ]
            if token:
                command.extend(["--continuation-token", token])
            result = subprocess.run(command, check=True, text=True, capture_output=True)
            payload = json.loads(result.stdout or "{}")
            keys.extend(item["Key"] for item in payload.get("Contents", []))
            token = payload.get("NextContinuationToken")
            if not token:
                return keys

    def object_exists(self, bucket: str, key: str) -> bool:
        result = subprocess.run(
            ["aws", "s3api", "head-object", "--bucket", bucket, "--key", key],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            return True
        stderr = result.stderr or ""
        if "Not Found" in stderr or "404" in stderr or "NoSuchKey" in stderr:
            return False
        raise RuntimeError(stderr.strip() or f"head-object failed for s3://{bucket}/{key}")


if __name__ == "__main__":
    raise SystemExit(main())
