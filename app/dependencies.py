from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.services.bedrock_service import BedrockService
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService
from app.services.guardrail_service import GuardrailService
from app.services.evaluation_service import EvaluationService
from app.services.session_service import SessionService


def get_bedrock_service(settings: Settings = Depends(get_settings)) -> BedrockService:
    return BedrockService(settings)


def get_embedding_service(settings: Settings = Depends(get_settings)) -> EmbeddingService:
    return EmbeddingService(settings)


def get_rag_service(
    settings: Settings = Depends(get_settings),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> RAGService:
    return RAGService(settings, embedding_service)


def get_guardrail_service(settings: Settings = Depends(get_settings)) -> GuardrailService:
    return GuardrailService(settings)


def get_evaluation_service(
    rag_service: RAGService = Depends(get_rag_service),
) -> EvaluationService:
    return EvaluationService(rag_service)


def get_session_service(
    settings: Settings = Depends(get_settings),
) -> SessionService:
    return SessionService(settings)


def require_api_key(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    # When APP_API_KEY is unset, local development remains frictionless.
    if not settings.APP_API_KEY:
        return

    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    if x_api_key == settings.APP_API_KEY or bearer_token == settings.APP_API_KEY:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key.",
    )
