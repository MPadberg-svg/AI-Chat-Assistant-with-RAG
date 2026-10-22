"""Application configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__version__ = "1.2.0"


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_chat_model: str = Field("gpt-4o-mini", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(
        "text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    embedding_batch_size: int = Field(128, alias="EMBEDDING_BATCH_SIZE", ge=1, le=2048)

    chroma_persist_dir: str = Field("./chroma_db", alias="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field("documents_v2", alias="CHROMA_COLLECTION")
    legacy_chroma_collection: str = Field("documents", alias="LEGACY_CHROMA_COLLECTION")

    chunk_size: int = Field(512, alias="CHUNK_SIZE", ge=64)
    chunk_overlap: int = Field(50, alias="CHUNK_OVERLAP", ge=0)
    top_k: int = Field(5, alias="TOP_K", ge=1, le=20)
    min_relevance_score: float = Field(0.0, alias="MIN_RELEVANCE_SCORE", ge=0, le=1)
    max_history_messages: int = Field(20, alias="MAX_HISTORY_MESSAGES", ge=0, le=200)

    client_url: str = Field("http://localhost:5173", alias="CLIENT_URL")
    extra_client_urls: str = Field("", alias="EXTRA_CLIENT_URLS")

    max_upload_bytes: int = Field(20 * 1024 * 1024, alias="MAX_UPLOAD_BYTES", ge=1024)

    # Optional hardening. Both are disabled by default so existing deployments
    # keep working unchanged; enable them for anything internet-facing.
    api_token: str = Field("", alias="API_TOKEN")
    rate_limit_per_minute: int = Field(0, alias="RATE_LIMIT_PER_MINUTE", ge=0)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, value: str) -> str:
        """Ensure OPENAI_API_KEY is present and non-empty."""
        if not value.strip():
            raise ValueError("OPENAI_API_KEY must be set")
        return value.strip()

    @model_validator(mode="after")
    def validate_chunking(self) -> "Settings":
        """Chunk overlap must be smaller than the chunk size."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def cors_origins(self) -> list[str]:
        """Allowed browser origins, combining CLIENT_URL and EXTRA_CLIENT_URLS."""
        origins = [self.client_url.strip()]
        origins.extend(
            origin.strip()
            for origin in self.extra_client_urls.split(",")
            if origin.strip()
        )
        return [origin for origin in origins if origin]

    @property
    def auth_enabled(self) -> bool:
        """True when API_TOKEN is configured."""
        return bool(self.api_token.strip())

    @property
    def rate_limit_enabled(self) -> bool:
        """True when RATE_LIMIT_PER_MINUTE is configured."""
        return self.rate_limit_per_minute > 0


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
