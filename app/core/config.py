"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "AI Document Q&A API"
    environment: str = "development"
    debug: bool = True

    # Security
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/ragdb"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_ttl_seconds: int = 900

    # AI Providers
    llm_provider: str = "openai"
    embedding_provider: str = "openai"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1"
    openai_embedding_model: str = "text-embedding-3-small"

    ollama_base_url: str = "http://ollama:11434"
    ollama_chat_model: str = "llama3"
    ollama_embedding_model: str = "nomic-embed-text"

    # RAG
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k: int = 5
    llm_temperature: float = 0

    # Uploads
    max_upload_size_mb: int = 25
    upload_dir: str = "./storage/documents"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        """Return database_url guaranteed to use the asyncpg driver.

        Most managed Postgres providers (Render, Railway, Supabase, Neon, Heroku, ...)
        hand out a plain `postgresql://` or `postgres://` connection string. SQLAlchemy
        interprets a driverless `postgresql://` scheme as the *sync* psycopg2 dialect,
        which this project does not depend on and does not install, causing
        `ModuleNotFoundError: No module named 'psycopg2'` at startup even though the
        async engine (asyncpg) is fully configured. Normalize the scheme here so any
        plain Postgres URL works without the operator needing to remember to add
        `+asyncpg` by hand.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()