import json
from datetime import timedelta

from report_generator.s3_keys import processed_prefix
from report_generator.time_window import parse_window_bound


class S3ProcessedReader:
    def __init__(self, bucket_name: str):
        import boto3

        self.bucket_name = bucket_name
        self.client = boto3.client("s3")

    def read_hour(self, factory_id: str, datasets: list[str], hour_window: dict) -> dict[str, list[dict]]:
        start_utc = parse_window_bound(hour_window.get("start_utc") or hour_window["start_kst"])
        end_utc = parse_window_bound(hour_window.get("end_utc") or hour_window["end_kst"])
        records_by_dataset = {}
        for dataset in datasets:
            records = []
            for prefix in _prefixes_for_window(factory_id, dataset, start_utc, end_utc):
                for key in self._list_keys(prefix):
                    records.append(self._get_json(key))
            records_by_dataset[dataset] = records
        return records_by_dataset

    def read_json(self, key: str) -> dict:
        return self._get_json(key)

    def _list_keys(self, prefix: str) -> list[str]:
        keys = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            keys.extend(item["Key"] for item in page.get("Contents", []))
        return keys

    def _get_json(self, key: str) -> dict:
        obj = self.client.get_object(Bucket=self.bucket_name, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))


def _prefixes_for_window(factory_id: str, dataset: str, start_utc, end_utc) -> list[str]:
    prefixes = []
    current = start_utc.replace(minute=0, second=0, microsecond=0)
    last = end_utc.replace(minute=0, second=0, microsecond=0)
    while current <= last:
        prefixes.append(processed_prefix(factory_id, dataset, current))
        current += timedelta(hours=1)
    return prefixes


class CloudInfraReader:
    def __init__(self, bucket_name: str):
        import boto3

        self.bucket_name = bucket_name
        self.client = boto3.client("s3")

    def read_hour(self, hour_window: dict) -> dict[str, list[dict]]:
        start_utc = parse_window_bound(hour_window.get("start_utc") or hour_window["start_kst"])
        end_utc = parse_window_bound(hour_window.get("end_utc") or hour_window["end_kst"])
        records_by_stream = {"fast": [], "slow": []}
        for stream in records_by_stream:
            for prefix in _cloud_infra_prefixes_for_window(stream, start_utc, end_utc):
                for key in self._list_keys(prefix):
                    record = self._get_json(key)
                    record.setdefault("_s3_key", key)
                    records_by_stream[stream].append(record)
        return records_by_stream

    def read_json(self, key: str) -> dict:
        return self._get_json(key)

    def _list_keys(self, prefix: str) -> list[str]:
        keys = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            keys.extend(item["Key"] for item in page.get("Contents", []))
        return keys

    def _get_json(self, key: str) -> dict:
        obj = self.client.get_object(Bucket=self.bucket_name, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))


def _cloud_infra_prefixes_for_window(stream: str, start_utc, end_utc) -> list[str]:
    prefixes = []
    current = start_utc.replace(minute=0, second=0, microsecond=0)
    last = end_utc.replace(minute=0, second=0, microsecond=0)
    while current <= last:
        prefixes.append(
            "processed/cloud_infra/"
            f"{stream}/yyyy={current.year:04d}/mm={current.month:02d}/"
            f"dd={current.day:02d}/hh={current.hour:02d}/"
        )
        current += timedelta(hours=1)
    return prefixes
