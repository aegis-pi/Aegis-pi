import json
import os


class BedrockReportClient:
    def __init__(self):
        import boto3

        self.model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.max_tokens = int(os.environ.get("BEDROCK_MAX_TOKENS", "3000"))
        self.temperature = float(os.environ.get("BEDROCK_TEMPERATURE", "0.2"))
        self.client = boto3.client("bedrock-runtime")

    def generate(self, prompt: str) -> str:
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }).encode("utf-8"),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read().decode("utf-8"))
        return "".join(
            block.get("text", "")
            for block in payload.get("content", [])
            if block.get("type") == "text"
        )


class MockBedrockReportClient:
    model_id = "mock-bedrock"

    def __init__(self, response: str):
        self.response = response
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response
