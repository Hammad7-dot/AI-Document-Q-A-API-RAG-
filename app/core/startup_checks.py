"""Fail-fast configuration validation run once at application startup.

These checks exist because misconfiguration here doesn't fail loudly on its
own: an embedding-dimension mismatch only surfaces the first time a document
is uploaded (as a cryptic pgvector "expected N dimensions" error), and a weak
JWT secret doesn't fail at all, it just silently makes tokens forgeable.
Catching both at boot turns a confusing runtime/security issue into an
immediate, readable startup error.
"""
from app.core.config import Settings
from app.models.document import EMBEDDING_DIM

# Output dimension for each (provider, model) pair we support. Extend this
# when adding a new provider or model so a mismatch is caught here instead of
# on the first upload.
KNOWN_EMBEDDING_DIMENSIONS: dict[tuple[str, str], int] = {
    ("openai", "text-embedding-3-small"): 1536,
    ("openai", "text-embedding-3-large"): 3072,
    ("openai", "text-embedding-ada-002"): 1536,
    ("google", "models/embedding-001"): 768,
    ("google", "models/text-embedding-004"): 768,
    ("cohere", "embed-english-v3.0"): 1024,
    ("cohere", "embed-english-light-v3.0"): 384,
    ("cohere", "embed-multilingual-v3.0"): 1024,
    ("cohere", "embed-multilingual-light-v3.0"): 384,
    ("ollama", "nomic-embed-text"): 768,
}


def _active_embedding_model(settings: Settings) -> str:
    return {
        "openai": settings.openai_embedding_model,
        "google": settings.google_embedding_model,
        "cohere": settings.cohere_embedding_model,
        "ollama": settings.ollama_embedding_model,
    }.get(settings.embedding_provider, "")


def validate_embedding_dimension(settings: Settings) -> None:
    """Raise if the configured embedding provider/model doesn't match the
    document_chunks.embedding column size. Unknown (provider, model) pairs are
    skipped rather than rejected, since a custom or newly-released model may
    not be in KNOWN_EMBEDDING_DIMENSIONS yet.
    """
    model = _active_embedding_model(settings)
    expected = KNOWN_EMBEDDING_DIMENSIONS.get((settings.embedding_provider, model))
    if expected is not None and expected != EMBEDDING_DIM:
        raise RuntimeError(
            f"Embedding dimension mismatch: {settings.embedding_provider}/{model} "
            f"produces {expected}-dimensional vectors, but document_chunks.embedding "
            f"is sized for {EMBEDDING_DIM} dimensions. Update EMBEDDING_DIM in "
            "app/models/document.py and apply a matching Alembic migration before "
            "switching providers."
        )
