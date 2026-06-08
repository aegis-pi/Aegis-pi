import logging
import os
from datetime import datetime, timezone

from processor import dynamo, s3_writer
from processor.envelope import EnvelopeError, parse
from processor.normalizer import normalize_factory_state, normalize_image_snapshot, normalize_infra_state
from processor.pipeline_status import calculate as calc_pipeline_status
from processor.risk import calculate as calc_risk

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    event = event or {}
    if event.get("action") == "refresh_pipeline_status":
        return _refresh_pipeline_status(event)

    logger.info(
        "Received: message_id=%s factory_id=%s source_type=%s",
        event.get("message_id"),
        event.get("factory_id"),
        event.get("source_type"),
    )

    try:
        envelope = parse(event)
    except EnvelopeError as exc:
        logger.error("Envelope validation failed: %s", exc)
        return {"status": "skipped", "reason": str(exc)}

    factory_id = envelope["factory_id"]
    source_type = envelope["source_type"]
    message_id = envelope["message_id"]
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    try:
        if source_type == "factory_state":
            _process_factory_state(envelope, factory_id, message_id, now, now_iso)
        elif source_type == "infra_state":
            _process_infra_state(envelope, factory_id, message_id, now, now_iso)
        else:
            _process_image_snapshot(envelope, factory_id, message_id, now_iso)
    except Exception as exc:
        logger.exception("Processing failed for message_id=%s: %s", message_id, exc)
        raise

    return {"status": "ok", "message_id": message_id}


def _refresh_pipeline_status(event):
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    factories = event.get("factories") or _factory_ids()
    results = []

    for factory_id in factories:
        latest = dynamo.get_latest_state(factory_id)
        if not latest:
            results.append({"factory_id": factory_id, "status": "missing"})
            continue

        pipeline_status = calc_pipeline_status(latest.get("last_infra_state_at"), now)
        latest_factory_state = latest.get("factory_state")
        risk = (
            calc_risk(latest_factory_state, latest.get("infra_state"), pipeline_status)
            if latest_factory_state
            else None
        )
        state_snapshot = dynamo.write_pipeline_status_snapshot(factory_id, pipeline_status, now_iso, risk)
        if state_snapshot:
            s3_writer.write_state_snapshot(factory_id, now_iso, state_snapshot)

        results.append({
            "factory_id": factory_id,
            "pipeline_status": pipeline_status["status"],
            "risk_score": risk["score"] if risk else None,
        })
        logger.info(
            "pipeline refresh done: factory_id=%s pipeline_status=%s risk_score=%s",
            factory_id,
            pipeline_status["status"],
            risk["score"] if risk else None,
        )

    return {"status": "ok", "refreshed": results}


def _process_factory_state(envelope, factory_id, message_id, now, now_iso):
    normalized = normalize_factory_state(envelope["payload"])

    # Compute pipeline_status using the last known infra_state time in LATEST
    latest = dynamo.get_latest_state(factory_id)
    last_infra_state_at = latest.get("last_infra_state_at")
    pipeline_status = calc_pipeline_status(last_infra_state_at, now)
    risk = calc_risk(normalized, latest.get("infra_state"), pipeline_status)

    state_snapshot = dynamo.write_factory_state_snapshot(factory_id, envelope, normalized, risk, pipeline_status, now_iso)

    base_body = {
        "source_message_id": message_id,
        "factory_id": factory_id,
        "source_timestamp": envelope["source_timestamp"],
        "processed_at": now_iso,
        "data": normalized,
    }
    s3_writer.write_factory_state(factory_id, message_id, envelope["source_timestamp"], base_body)
    s3_writer.write_risk_score(
        factory_id,
        message_id,
        envelope["source_timestamp"],
        {**base_body, "risk": risk, "pipeline_status": pipeline_status},
    )
    if state_snapshot:
        s3_writer.write_state_snapshot(factory_id, now_iso, state_snapshot)

    logger.info(
        "factory_state done: factory_id=%s risk_score=%.2f risk_level=%s pipeline_status=%s",
        factory_id, risk["score"], risk["level"], pipeline_status["status"],
    )


def _process_infra_state(envelope, factory_id, message_id, now, now_iso):
    normalized = normalize_infra_state(envelope["payload"])
    # infra_state just arrived → pipeline_status is normal (age ≈ 0)
    pipeline_status = calc_pipeline_status(envelope["source_timestamp"], now)
    latest = dynamo.get_latest_state(factory_id)
    latest_factory_state = latest.get("factory_state")
    risk = calc_risk(latest_factory_state, normalized, pipeline_status) if latest_factory_state else None

    state_snapshot = dynamo.write_infra_state_snapshot(factory_id, envelope, normalized, pipeline_status, now_iso, risk)

    s3_writer.write_infra_state(
        factory_id,
        message_id,
        envelope["source_timestamp"],
        {
            "source_message_id": message_id,
            "factory_id": factory_id,
            "source_timestamp": envelope["source_timestamp"],
            "processed_at": now_iso,
            "data": normalized,
            "pipeline_status": pipeline_status,
        },
    )
    if state_snapshot:
        s3_writer.write_state_snapshot(factory_id, now_iso, state_snapshot)

    logger.info(
        "infra_state done: factory_id=%s pipeline_status=%s nodes_ready=%d/%d",
        factory_id,
        pipeline_status["status"],
        normalized.get("nodes_ready", 0),
        normalized.get("nodes_total", 0),
    )


def _process_image_snapshot(envelope, factory_id, message_id, now_iso):
    normalized = normalize_image_snapshot(envelope["payload"])
    state_snapshot = dynamo.write_image_snapshot_reference(factory_id, envelope, normalized, now_iso)

    s3_writer.write_image_snapshot(
        factory_id,
        message_id,
        envelope["source_timestamp"],
        {
            "source_message_id": message_id,
            "factory_id": factory_id,
            "source_timestamp": envelope["source_timestamp"],
            "processed_at": now_iso,
            "data": normalized,
        },
    )
    if state_snapshot:
        s3_writer.write_state_snapshot(factory_id, now_iso, state_snapshot)

    logger.info(
        "image_snapshot done: factory_id=%s event_type=%s s3_key=%s",
        factory_id,
        normalized["event_type"],
        normalized["s3_key"],
    )


def _factory_ids() -> list[str]:
    return [
        item.strip()
        for item in os.environ.get("FACTORY_IDS", "factory-a,factory-b,factory-c").split(",")
        if item.strip()
    ]
