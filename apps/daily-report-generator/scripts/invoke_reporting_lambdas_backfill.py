#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


FUNCTIONS = {
    "prepare": "AEGIS-Lambda-PrepareReportWindow",
    "aggregate_factory_hour": "AEGIS-Lambda-AggregateFactoryHour",
    "merge_factory_daily": "AEGIS-Lambda-MergeFactoryDaily",
    "generate_factory_report": "AEGIS-Lambda-GenerateFactoryReport",
}


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    items = parse_target_dates(args.target_dates)
    if args.max_bedrock_calls is not None:
        items = items[: args.max_bedrock_calls]

    results = {
        "generated_at": utc_now(),
        "bucket": args.bucket,
        "dry_run": args.dry_run,
        "only_missing": args.only_missing,
        "items": [],
    }
    for target, report_date in items:
        try:
            item_result = run_item(target, report_date, args)
        except Exception as exc:  # noqa: BLE001
            item_result = {
                "target": target,
                "report_date": report_date,
                "status": "failed",
                "error": repr(exc),
            }
        results["items"].append(item_result)
        write_results(args.output_dir, results)

    write_results(args.output_dir, results)
    print_summary(args.output_dir, results)
    failed_count = sum(1 for item in results["items"] if item["status"] in ("failed", "validation_failed"))
    return 2 if failed_count else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill daily factory reports by invoking deployed reporting Lambdas.")
    parser.add_argument("--bucket", default="aegis-bucket-data")
    parser.add_argument("--target-dates", required=True)
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-bedrock-calls", type=int)
    parser.add_argument("--hour-concurrency", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/aegis-reporting-backfill"))
    return parser.parse_args()


def parse_target_dates(value: str) -> list[tuple[str, str]]:
    items = []
    for raw_item in value.split(","):
        raw_item = raw_item.strip()
        if not raw_item:
            continue
        target, report_date = raw_item.split(":", 1)
        if target not in ("factory-a", "factory-b", "factory-c"):
            raise SystemExit(f"unsupported target for factory Lambda backfill: {target}")
        datetime.fromisoformat(report_date)
        items.append((target, report_date))
    return items


def run_item(target: str, report_date: str, args: argparse.Namespace) -> dict:
    output_prefix = report_prefix(target, report_date)
    report_key = f"{output_prefix}/report.md"
    metadata_key = f"{output_prefix}/generation-metadata.json"
    has_report = s3_object_exists(args.bucket, report_key)
    has_metadata = s3_object_exists(args.bucket, metadata_key)
    base = {
        "target": target,
        "report_date": report_date,
        "output_prefix": output_prefix,
        "report_key": report_key,
        "metadata_key": metadata_key,
        "has_report_md": has_report,
        "has_generation_metadata": has_metadata,
    }
    if args.only_missing and has_report and has_metadata:
        return {**base, "status": "skipped_complete"}
    if args.dry_run:
        return {**base, "status": "would_generate"}

    prepared = invoke_lambda(FUNCTIONS["prepare"], {
        "report_date": report_date,
        "timezone": args.timezone,
        "factories": [target],
    })
    factory_item = next(item for item in prepared["factory_items"] if item["factory_id"] == target)
    with ThreadPoolExecutor(max_workers=args.hour_concurrency) as executor:
        hour_results = list(executor.map(lambda hour_item: invoke_lambda(FUNCTIONS["aggregate_factory_hour"], {
            "factory_id": target,
            "report_date": report_date,
            "timezone": args.timezone,
            "datasets": factory_item["datasets"],
            "output_prefix": factory_item["output_prefix"],
            "hour": hour_item["hour"],
            "hour_window": hour_item["hour_window"],
        }), factory_item["hour_items"]))
    merged = invoke_lambda(FUNCTIONS["merge_factory_daily"], {
        "factory_id": target,
        "report_date": report_date,
        "timezone": args.timezone,
        "output_prefix": factory_item["output_prefix"],
        "hour_results": hour_results,
    })
    generated = invoke_lambda(FUNCTIONS["generate_factory_report"], {
        "output_prefix": factory_item["output_prefix"],
        "context_key": merged["context_key"],
    })
    status = generated.get("status", "failed")
    result = {
        **base,
        "status": status,
        "daily_summary_key": merged.get("daily_summary_key"),
        "context_key": merged.get("context_key"),
    }
    if status == "success":
        result["report_key"] = generated.get("report_key")
        result["metadata_key"] = generated.get("metadata_key")
    else:
        result["validation_errors"] = generated.get("validation_errors", [])
        result["error"] = generated.get("error")
    return result


def invoke_lambda(function_name: str, payload: dict) -> dict:
    output_path = Path("/tmp/aegis-reporting-backfill") / f"lambda-{function_name}-{datetime.now().timestamp()}.json"
    command = [
        "aws",
        "lambda",
        "invoke",
        "--function-name",
        function_name,
        "--cli-binary-format",
        "raw-in-base64-out",
        "--cli-connect-timeout",
        "30",
        "--cli-read-timeout",
        "300",
        "--payload",
        json.dumps(payload, separators=(",", ":")),
        str(output_path),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    metadata = json.loads(result.stdout or "{}")
    response = json.loads(output_path.read_text(encoding="utf-8") or "{}")
    if "FunctionError" in metadata:
        raise RuntimeError(json.dumps(response, ensure_ascii=False))
    return response


def s3_object_exists(bucket: str, key: str) -> bool:
    result = subprocess.run(
        ["aws", "s3api", "head-object", "--bucket", bucket, "--key", key],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    stderr = result.stderr or ""
    if "404" in stderr or "Not Found" in stderr or "NoSuchKey" in stderr:
        return False
    raise RuntimeError(stderr.strip() or f"head-object failed for s3://{bucket}/{key}")


def report_prefix(target: str, report_date: str) -> str:
    return (
        f"reports/daily/yyyy={report_date[0:4]}/"
        f"mm={report_date[5:7]}/dd={report_date[8:10]}/{target}"
    )


def write_results(output_dir: Path, results: dict) -> None:
    (output_dir / "backfill-results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "backfill-results.md").write_text(render_markdown(results), encoding="utf-8")


def render_markdown(results: dict) -> str:
    lines = [
        "# Daily Report Backfill Results",
        "",
        f"- generated_at: {results['generated_at']}",
        f"- bucket: {results['bucket']}",
        f"- dry_run: {str(results['dry_run']).lower()}",
        "",
        "| target | report_date | status | report_key | context_key |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in results["items"]:
        lines.append(
            f"| {item['target']} | {item['report_date']} | {item['status']} | "
            f"{item.get('report_key', '')} | {item.get('context_key', '')} |"
        )
    failures = [item for item in results["items"] if item["status"] in ("failed", "validation_failed")]
    if failures:
        lines.extend(["", "## Failures", ""])
        for item in failures:
            lines.append(f"- {item['target']} {item['report_date']}: {item.get('error') or item.get('validation_errors')}")
    return "\n".join(lines) + "\n"


def print_summary(output_dir: Path, results: dict) -> None:
    status_counts = {}
    for item in results["items"]:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    print(f"results_json={output_dir / 'backfill-results.json'}")
    print(f"results_markdown={output_dir / 'backfill-results.md'}")
    print(f"status_counts={json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    sys.exit(main())
