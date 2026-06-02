from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote_plus


@dataclass(frozen=True)
class S3ObjectRef:
    bucket: str
    key: str


def object_refs(event: dict) -> list[S3ObjectRef]:
    refs = []
    for record in event.get("Records") or []:
        s3 = record.get("s3") or {}
        bucket = (s3.get("bucket") or {}).get("name")
        key = (s3.get("object") or {}).get("key")
        if bucket and key:
            refs.append(S3ObjectRef(bucket=bucket, key=unquote_plus(key)))
    return refs
