"""Application settings.

All configuration lives in a single ``Settings`` object loaded from environment
variables (and an optional ``.env`` file). No scattered globals, no ad-hoc
``os.getenv`` calls elsewhere in the codebase.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, PostgresDsn, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.shared.parsing import parse_str_list


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    name: str = "knowledge-service"
    env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    log_json: bool = False
    # NoDecode disables pydantic-settings' automatic JSON source decoding so the
    # raw env string reaches the validator, which accepts both comma-separated
    # and JSON-array formats.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string or a JSON array for CORS origins."""
        return parse_str_list(value)

    @property
    def is_production(self) -> bool:
        return self.env == Environment.PRODUCTION


class DatabaseSettings(BaseSettings):
    """PostgreSQL / SQLAlchemy settings."""

    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "knowledge"
    password: str = "knowledge"
    name: str = "knowledge"
    echo: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_dsn(self) -> str:
        """Async DSN for SQLAlchemy (asyncpg driver)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                path=self.name,
            )
        )


class VectorSettings(BaseSettings):
    """Qdrant settings (reserved — not wired yet)."""

    model_config = SettingsConfigDict(env_prefix="VECTOR_", extra="ignore")

    host: str = "localhost"
    port: int = 6333
    collection: str = "knowledge_chunks"


class LLMSettings(BaseSettings):
    """LLM + embeddings settings (Ollama, external — reserved)."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"


class EmbeddingSettings(BaseSettings):
    """Embedding provider settings (reserved)."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", extra="ignore")

    model: str = "bge-m3"


class StorageSettings(BaseSettings):
    """Binary storage settings."""

    model_config = SettingsConfigDict(env_prefix="STORAGE_", extra="ignore")

    local_path: str = "./storage"
    page_image_format: str = "webp"


class UploadSettings(BaseSettings):
    """Document upload validation policy.

    List fields use ``NoDecode`` + the reusable ``parse_str_list`` parser so
    envs accept both comma-separated and JSON-array formats.
    """

    model_config = SettingsConfigDict(env_prefix="UPLOAD_", extra="ignore")

    max_size_mb: int = 50
    allowed_extensions: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["pdf"])
    allowed_mime_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["application/pdf"]
    )

    @field_validator("allowed_extensions", "allowed_mime_types", mode="before")
    @classmethod
    def _parse_lists(cls, value: object) -> object:
        return parse_str_list(value)

    @field_validator("allowed_extensions", mode="after")
    @classmethod
    def _normalize_extensions(cls, value: list[str]) -> list[str]:
        return [ext.lstrip(".").lower() for ext in value]

    @property
    def max_size_bytes(self) -> int:
        return self.max_size_mb * 1024 * 1024


class ProcessingSettings(BaseSettings):
    """Asynchronous processing pipeline settings."""

    model_config = SettingsConfigDict(env_prefix="PROCESSING_", extra="ignore")

    max_retries: int = 3
    default_priority: int = 0
    dispatch_batch_size: int = 10


class Settings(BaseSettings):
    """Root settings object. The single source of truth for configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton ``Settings`` instance."""
    return Settings()
