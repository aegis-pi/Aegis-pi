from __future__ import annotations

import json
import logging
import os

import boto3

from alert_dispatcher import dedupe, s3_event, slack
from alert_dispatcher.rules import evaluate
from alert_dispatcher.snapshot_parser import parse_source
from alert_dispatcher.time_utils import epoch_seconds, utc_now


logger = logging.getLogger()
logger.setLevel(logging.INFO)

_s3 = boto3.client("s3")


def handler(event, context):
    now = utc_now()
    now_epoch = epoch_seconds(now)
    results = []

    for ref in s3_event.object_refs(event or {}):
        source = parse_source(ref.key)
        if not source:
            results.append({"key": ref.key, "status": "skipped", "reason": "unsupported_key"})
            continue

        snapshot = _read_json(ref.bucket, ref.key)
        alerts = evaluate(source, snapshot)
        if not alerts:
            results.append({"key": ref.key, "status": "skipped", "reason": "normal"})
            continue

        for alert in alerts:
            result = _dispatch(alert, now_epoch)
            results.append({"key": ref.key, "alert": alert.sk, **result})

    return {"status": "ok", "results": results}


def _dispatch(alert, now_epoch: int) -> dict:
    if not _slack_configured():
        logger.info("Slack webhook is not configured; skipping alert=%s/%s", alert.pk, alert.sk)
        return {"status": "skipped", "reason": "slack_not_configured"}

    confirmation = dedupe.confirm(alert, now_epoch)
    if not confirmation.get("confirmed"):
        return {
            "status": "skipped",
            "reason": confirmation.get("reason"),
            "observation_count": confirmation.get("observation_count"),
            "required_observations": confirmation.get("required_observations"),
        }

    reservation = dedupe.reserve(alert, now_epoch)
    if not reservation.get("reserved"):
        return {"status": "skipped", "reason": reservation.get("reason")}

    try:
        response = slack.send(alert)
    except Exception as exc:
        logger.exception("Slack send failed: alert=%s/%s", alert.pk, alert.sk)
        dedupe.record_slack_result(alert, "failed", str(exc))
        return {"status": "failed", "reason": "slack_send_failed", "error": str(exc)}

    dedupe.record_slack_result(alert, "sent", None)
    return {"status": "sent", "slack_status_code": response.get("status_code")}


def _read_json(bucket: str, key: str) -> dict:
    response = _s3.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    return json.loads(body)


def _slack_configured() -> bool:
    return bool(os.environ.get("SLACK_WEBHOOK_SECRET_ID") or os.environ.get("SLACK_WEBHOOK_SSM_PARAMETER_NAME"))
