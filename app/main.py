from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api import chat_routes, document_routes, agent_routes, ticket_routes, evaluation_routes
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def _allowed_origins() -> list[str]:
    raw = settings.ALLOWED_ORIGINS.strip()
    if not raw or raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Enterprise AI Ops Copilot", env=settings.APP_ENV)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Enterprise AI Ops Copilot",
    description="AI-powered operations assistant using AWS Bedrock, LangGraph, and RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_routes.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(document_routes.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(agent_routes.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(ticket_routes.router, prefix="/api/v1/tickets", tags=["Tickets"])
app.include_router(evaluation_routes.router, prefix="/api/v1/evaluation", tags=["Evaluation"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "env": settings.APP_ENV}
