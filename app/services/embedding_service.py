import json
import time
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import Settings
from app.utils.timer import timed
from app.services.logging_service import get_logger

logger = get_logger(__name__)

EMBEDDING_DIMENSION = 1536  # Titan Embed Text V2 default
INTER_REQUEST_DELAY = 2.0   # seconds between calls — respects new-account rate limits


def _is_throttling(exc: BaseException) -> bool:
    return isinstance(exc, ClientError) and exc.response["Error"]["Code"] == "ThrottlingException"


class EmbeddingService:
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
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        retry=retry_if_exception_type(ClientError),
        reraise=True,
    )
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string using Amazon Titan Embeddings V2."""
        client = self._get_client()
        body = json.dumps({"inputText": text[:8000]})

        with timed("bedrock_embed") as t:
            try:
                response = client.invoke_model(
                    modelId=self.settings.BEDROCK_EMBEDDING_MODEL_ID,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )
            except NoCredentialsError:
                raise RuntimeError("AWS credentials not configured.")
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == "ThrottlingException":
                    logger.warning("Embedding throttled — retrying with backoff")
                else:
                    logger.error("Embedding ClientError", code=code, error=str(e))
                raise

        result = json.loads(response["body"].read())
        embedding = result.get("embedding", [])

        logger.info("embed_complete", dim=len(embedding), latency_ms=t.get("elapsed_ms", 0.0))
        return embedding

    async def embed_batch(
        self,
        texts: list[str],
        delay: float = INTER_REQUEST_DELAY,
    ) -> list[list[float]]:
        """Embed texts one by one with a delay between each call."""
        embeddings = []
        for i, text in enumerate(texts):
            emb = await self.embed(text)
            embeddings.append(emb)
            if (i + 1) % 5 == 0:
                logger.info("embed_batch_progress", done=i + 1, total=len(texts))
            if i < len(texts) - 1:
                time.sleep(delay)
        return embeddings
