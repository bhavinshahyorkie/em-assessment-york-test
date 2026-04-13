"""OpenAI text embeddings used as dense vectors for semantic similarity."""

from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


def _truncate(text: str, max_chars: int = 24000) -> str:
    """Cap input length to stay within model context limits for a single embedding call."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


class EmbeddingClient:
    """
    Lazy OpenAI client: do not instantiate in __init__.

    The OpenAI SDK raises if api_key is missing. FastAPI runs `Depends(get_embedder)`
    before the route body, so we must not build the client until after the route checks
    `OPENAI_API_KEY` (otherwise missing keys become an uncaught 500).
    """

    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            key = settings.openai_api_key
            if not key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            self._client = OpenAI(api_key=key)
        return self._client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per string, order preserved (batch API call)."""
        if not texts:
            return []
        inputs = [_truncate(t) for t in texts]
        resp = self._get_client().embeddings.create(model=settings.embedding_model, input=inputs)
        ordered = sorted(resp.data, key=lambda x: x.index)
        return [item.embedding for item in ordered]
