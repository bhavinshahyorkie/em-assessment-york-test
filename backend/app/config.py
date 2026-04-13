from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `.env` from the `backend/` package root so the key loads even if uvicorn's cwd is not `backend/`.
_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    top_k: int = 10


settings = Settings()
