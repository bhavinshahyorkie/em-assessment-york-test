"""Application settings loaded from environment and `backend/.env` (never commit secrets)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents: core -> app -> backend
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Env-driven config. Secrets (e.g. API keys) must live in `.env` or the process environment only."""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    top_k: int = 10


settings = Settings()
