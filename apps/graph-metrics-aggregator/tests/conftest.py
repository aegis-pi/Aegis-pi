import sys
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _Key:
    def __init__(self, name):
        self.name = name

    def eq(self, value):
        return ("eq", self.name, value)

    def between(self, start, end):
        return ("between", self.name, start, end)

    def __and__(self, other):
        return ("and", self, other)


sys.modules.setdefault(
    "boto3",
    SimpleNamespace(
        resource=lambda service: SimpleNamespace(Table=lambda name: None),
        client=lambda service: None,
    ),
)
sys.modules.setdefault("boto3.dynamodb", SimpleNamespace())
sys.modules.setdefault("boto3.dynamodb.conditions", SimpleNamespace(Key=_Key))
