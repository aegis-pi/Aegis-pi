import json


def load_json_bytes(body: bytes) -> dict:
    return json.loads(body.decode("utf-8"))

