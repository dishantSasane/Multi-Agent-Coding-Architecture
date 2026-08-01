"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://codeforge:codeforge_pass@db:5432/codeforge",
        description="PostgreSQL connection string",
    )

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://redis:6379/0",
        description="Redis connection string",
    )

    # LLM API Keys
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    kimi_api_key: str | None = Field(default=None, description="Kimi API key")
    qwen_api_key: str | None = Field(default=None, description="Qwen API key")
    gemini_api_key: str | None = Field(default=None, description="Gemini API key")

    # LiteLLM
    litellm_master_key: str = Field(default="your-master-key", description="LiteLLM master key")
    litellm_salt_key: str = Field(default="your-salt-key", description="LiteLLM salt key")

    # Sandbox Configuration
    sandbox_timeout: int = Field(default=30, ge=1, le=300, description="Sandbox execution timeout in seconds")
    sandbox_memory_limit: str = Field(default="512m", description="Sandbox memory limit")
    sandbox_cpu_limit: float = Field(default=1.0, ge=0.1, le=4.0, description="Sandbox CPU limit")

    # Circuit Breaker
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, description="Failures before opening circuit")
    circuit_breaker_recovery_timeout: int = Field(default=30, ge=5, description="Seconds before attempting recovery")

    # Application
    log_level: str = Field(default="INFO", description="Logging level")
    max_correction_attempts: int = Field(default=3, ge=1, le=10, description="Maximum self-correction retries")
    default_ensemble_size: int = Field(default=3, ge=1, le=5, description="Number of models in ensemble")
    secret_key: str = Field(default="change-me-in-production", description="Secret key for JWT")

    # Model timeouts
    default_model_timeout: int = Field(default=30, ge=5, le=120, description="Default LLM timeout in seconds")
    reasoning_model_timeout: int = Field(default=120, ge=30, le=300, description="Timeout for reasoning models")

    # Validation
    hypothesis_iterations: int = Field(default=100, ge=10, le=1000, description="Hypothesis test iterations")

    @property
    def llm_api_keys(self) -> dict[str, str | None]:
        """Return dictionary of all LLM API keys."""
        return {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "kimi": self.kimi_api_key,
            "qwen": self.qwen_api_key,
            "gemini": self.gemini_api_key,
        }

    def get_enabled_providers(self) -> list[str]:
        """Return list of providers with configured API keys."""
        return [provider for provider, key in self.llm_api_keys.items() if key is not None]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
