from alert_dispatcher.snapshot_parser import parse_source


def test_parse_factory_state_snapshot_key():
    source = parse_source("processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=01/x.json")

    assert source.source_type == "factory_state_snapshot"
    assert source.scope == "factory-c"
    assert source.status == "state_snapshot"


def test_parse_cloud_infra_keys():
    fast = parse_source("processed/cloud_infra/fast/yyyy=2026/mm=06/dd=02/hh=02/x.json")
    slow = parse_source("processed/cloud_infra/slow/yyyy=2026/mm=06/dd=02/hh=02/x.json")

    assert fast.source_type == "cloud_infra_fast"
    assert fast.scope == "cloud-infra"
    assert fast.status == "fast"
    assert slow.source_type == "cloud_infra_slow"
    assert slow.status == "slow"


def test_parse_unsupported_key_returns_none():
    assert parse_source("processed/factory-c/risk_score/yyyy=2026/mm=06/dd=02/hh=01/x.json") is None
