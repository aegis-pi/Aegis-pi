import importlib
import sys
from datetime import datetime, timezone
from types import SimpleNamespace


class FakeKey:
    def __init__(self, name):
        self.name = name

    def eq(self, value):
        return FakeExpression("eq", self.name, value)

    def between(self, start, end):
        return FakeExpression("between", self.name, start, end)


class FakeExpression:
    def __init__(self, *parts):
        self.parts = parts

    def __and__(self, other):
        return ("and", self, other)


class FakeTable:
    def __init__(self):
        self.calls = []
        self.put_items = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        if "ExclusiveStartKey" not in kwargs:
            return {"Items": [{"page": 1}], "LastEvaluatedKey": {"pk": "cursor"}}
        return {"Items": [{"page": 2}]}

    def put_item(self, Item):
        self.put_items.append(Item)


class FakeS3:
    def __init__(self):
        self.puts = []

    def put_object(self, **kwargs):
        self.puts.append(kwargs)


def test_query_history_handles_pagination_and_put_converts_float(monkeypatch):
    table = FakeTable()
    _install_boto3(monkeypatch, table=table)
    dynamo = importlib.import_module("aggregator.dynamo")

    items = dynamo.query_history(
        "factory-b",
        datetime(2026, 5, 28, 10, 5, tzinfo=timezone.utc),
        datetime(2026, 5, 28, 10, 9, 59, 999000, tzinfo=timezone.utc),
    )
    dynamo.put_graph_item({"pk": "FACTORY#factory-b", "sk": "GRAPH#5M#x", "value": 1.25})

    assert items == [{"page": 1}, {"page": 2}]
    assert len(table.calls) == 2
    assert table.calls[1]["ExclusiveStartKey"] == {"pk": "cursor"}
    assert str(table.put_items[0]["value"]) == "1.25"


def test_s3_body_excludes_dynamodb_ttl(monkeypatch):
    s3 = FakeS3()
    _install_boto3(monkeypatch, s3=s3)
    s3_writer = importlib.import_module("aggregator.s3_writer")

    key = s3_writer.put_graph_object(
        {
            "pk": "FACTORY#factory-b",
            "sk": "GRAPH#5M#2026-05-28T10:05:00Z",
            "factory_id": "factory-b",
            "bucket_start": "2026-05-28T10:05:00Z",
            "ttl": 123,
        }
    )

    assert key == "processed_agg/factory-b/metrics_5m/yyyy=2026/mm=05/dd=28/hh=10/mm=05.json"
    body = s3.puts[0]["Body"]
    assert '"ttl"' not in body
    assert '"dynamodb_pk": "FACTORY#factory-b"' in body
    assert '"dynamodb_sk": "GRAPH#5M#2026-05-28T10:05:00Z"' in body


def _install_boto3(monkeypatch, table=None, s3=None):
    for name in ["aggregator.dynamo", "aggregator.s3_writer", "boto3", "boto3.dynamodb", "boto3.dynamodb.conditions"]:
        sys.modules.pop(name, None)
    table = table or FakeTable()
    s3 = s3 or FakeS3()
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(resource=lambda service: SimpleNamespace(Table=lambda name: table), client=lambda service: s3),
    )
    monkeypatch.setitem(sys.modules, "boto3.dynamodb", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "boto3.dynamodb.conditions", SimpleNamespace(Key=FakeKey))
