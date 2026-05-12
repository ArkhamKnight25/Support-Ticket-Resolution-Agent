from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # AWS
    AWS_REGION: str = "eu-north-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Bedrock
    BEDROCK_CHAT_MODEL_ID: str = "arn:aws:bedrock:eu-north-1:382884104314:inference-profile/eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_GUARDRAIL_ID: str = ""
    BEDROCK_GUARDRAIL_VERSION: str = "DRAFT"

    # Vector Store
    VECTOR_STORE_TYPE: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    OPENSEARCH_ENDPOINT: str = ""
    OPENSEARCH_INDEX: str = "enterprise-ops"

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    API_PORT: int = 8000
    APP_API_KEY: str = ""
    SESSIONS_DIR: str = "data/sessions"
    ALLOWED_ORIGINS: str = "*"

    # Integrations
    SERVICENOW_MOCK: bool = True
    SERVICENOW_BASE_URL: str = ""
    SERVICENOW_USER: str = ""
    SERVICENOW_PASSWORD: str = ""

    SNOWFLAKE_MOCK: bool = True
    SNOWFLAKE_ACCOUNT: str = ""
    SNOWFLAKE_USER: str = ""
    SNOWFLAKE_PASSWORD: str = ""
    SNOWFLAKE_DATABASE: str = "OPS_DB"
    SNOWFLAKE_SCHEMA: str = "PUBLIC"
    SNOWFLAKE_WAREHOUSE: str = "COMPUTE_WH"

    TEAMS_MOCK: bool = True
    TEAMS_WEBHOOK_URL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
