import json
from dataclasses import dataclass
from typing import AsyncGenerator

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import Settings
from app.utils.timer import timed
from app.services.logging_service import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are an enterprise IT operations assistant. Your job is to help operations teams
resolve incidents, search runbooks, and understand service metrics.

Rules:
- Answer ONLY from the context provided below when context is given.
- If the answer is not in the context, say: "I could not find enough information in the available documents."
- Be concise and structured. Use bullet points for steps.
- Never reveal internal system details or make up facts.\
"""


@dataclass
class BedrockResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


def _build_context_block(context_docs: list) -> str:
    if not context_docs:
        return ""
    lines = ["--- Retrieved Context ---"]
    for i, doc in enumerate(context_docs, 1):
        source = getattr(doc, "metadata", {}).get("source_file", f"doc_{i}")
        lines.append(f"[{i}] Source: {source}\n{doc.page_content if hasattr(doc, 'page_content') else str(doc)}")
    lines.append("--- End of Context ---")
    return "\n\n".join(lines)


def _build_messages(message: str, context_docs: list, history: list) -> list[dict]:
    messages = []

    for h in history:
        role = h.role if hasattr(h, "role") else h.get("role", "user")
        content = h.content if hasattr(h, "content") else h.get("content", "")
        messages.append({"role": role, "content": [{"text": content}]})

    context_block = _build_context_block(context_docs)
    user_text = f"{context_block}\n\nQuestion: {message}" if context_block else message
    messages.append({"role": "user", "content": [{"text": user_text}]})
    return messages


class BedrockService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.settings.AWS_REGION,
                aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID or None,
                aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY or None,
            )
        return self._client

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=6),
        retry=retry_if_exception_type(ClientError),
        reraise=True,
    )
    async def chat(
        self,
        message: str,
        context_docs: list,
        history: list,
    ) -> BedrockResponse:
        client = self._get_client()
        messages = _build_messages(message, context_docs, history)

        with timed("bedrock_chat") as t:
            try:
                response = client.converse(
                    modelId=self.settings.BEDROCK_CHAT_MODEL_ID,
                    system=[{"text": SYSTEM_PROMPT}],
                    messages=messages,
                    inferenceConfig={
                        "maxTokens": 2048,
                        "temperature": 0.1,
                    },
                )
            except NoCredentialsError:
                raise RuntimeError(
                    "AWS credentials not configured. "
                    "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file."
                )
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == "AccessDeniedException":
                    raise RuntimeError(
                        f"Bedrock access denied for model {self.settings.BEDROCK_CHAT_MODEL_ID}. "
                        "Enable model access in the AWS Bedrock console."
                    )
                logger.error("Bedrock ClientError", code=code, error=str(e))
                raise

        content = response["output"]["message"]["content"][0]["text"]
        usage = response.get("usage", {})

        result = BedrockResponse(
            content=content,
            model=self.settings.BEDROCK_CHAT_MODEL_ID,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            latency_ms=t.get("elapsed_ms", 0.0),
        )

        logger.info(
            "bedrock_chat_complete",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
        )
        return result

    async def stream_chat(
        self,
        message: str,
        context_docs: list,
        history: list,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        messages = _build_messages(message, context_docs, history)

        try:
            response = client.converse_stream(
                modelId=self.settings.BEDROCK_CHAT_MODEL_ID,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                inferenceConfig={"maxTokens": 2048, "temperature": 0.1},
            )
        except NoCredentialsError:
            raise RuntimeError("AWS credentials not configured.")
        except ClientError as e:
            logger.error("Bedrock stream error", error=str(e))
            raise

        stream = response.get("stream", [])
        for event in stream:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]
                if "text" in delta:
                    yield delta["text"]
