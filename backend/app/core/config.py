"""Application configuration."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    chroma_persist_dir: str = Field("./chroma_db", alias="CHROMA_PERSIST_DIR")
    chunk_size: int = Field(512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(50, alias="CHUNK_OVERLAP")
    top_k: int = Field(5, alias="TOP_K")
    client_url: str = Field("http://localhost:5173", alias="CLIENT_URL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, value: str) -> str:
        """Ensure OPENAI_API_KEY is present and non-empty."""
        if not value.strip():
            raise ValueError("OPENAI_API_KEY must be set")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
