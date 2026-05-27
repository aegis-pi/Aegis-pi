import json


class S3ReportWriter:
    def __init__(self, bucket_name: str):
        import boto3

        self.bucket_name = bucket_name
        self.client = boto3.client("s3")

    def write_json(self, key: str, body: dict) -> str:
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json.dumps(body, ensure_ascii=False, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        return key

    def write_text(self, key: str, body: str, content_type: str = "text/markdown; charset=utf-8") -> str:
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType=content_type,
        )
        return key
