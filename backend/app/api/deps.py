"""FastAPI dependencies — inject parsers, embedders, and future services here."""

from app.parsers import default_registry
from app.services.embeddings import EmbeddingClient


def get_registry():
    """Shared `ParserRegistry` (PDF + DOCX) for all uploaded files."""
    return default_registry()


def get_embedder() -> EmbeddingClient:
    """Lazy OpenAI embedding client (see `EmbeddingClient`)."""
    return EmbeddingClient()
