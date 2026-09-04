"""Application configuration using Pydantic Settings."""

import os
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
    openrouter_api_key: str | None = Field(default=None, description="OpenRouter API key (free tier supported)")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    kimi_api_key: str | None = Field(default=None, description="Kimi API key")
    qwen_api_key: str | None = Field(default=None, description="Qwen API key")
    gemini_api_key: str | None = Field(default=None, description="Gemini API key")

    # OpenAI-compatible base URL override (e.g. https://openrouter.ai/api/v1)
    openai_api_base: str | None = Field(default=None, description="Override OpenAI base URL")

    # LiteLLM
    litellm_master_key: str = Field(default="your-master-key", description="LiteLLM master key")
    litellm_salt_key: str = Field(default="your-salt-key", description="LiteLLM salt key")

    # Sandbox Configuration
    sandbox_enabled: bool = Field(default=True, description="Enable Docker sandbox execution (set False to skip)")
    sandbox_timeout: int = Field(default=30, ge=1, le=300, description="Sandbox execution timeout in seconds")
    sandbox_memory_limit: str = Field(default="512m", description="Sandbox memory limit")
    sandbox_cpu_limit: float = Field(default=1.0, ge=0.1, le=4.0, description="Sandbox CPU limit")

    # Circuit Breaker
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, description="Failures before opening circuit")
    circuit_breaker_recovery_timeout: int = Field(default=30, ge=5, description="Seconds before attempting recovery")

    # Application
    log_level: str = Field(default="INFO", description="Logging level")
    max_correction_attempts: int = Field(default=3, ge=1, le=10, description="Maximum self-correction retries")
    default_ensemble_size: int = Field(default=2, ge=1, le=5, description="Number of models in ensemble")
    secret_key: str = Field(default="change-me-in-production", description="Secret key for JWT")

    # Model timeouts
    default_model_timeout: int = Field(default=30, ge=5, le=120, description="Default LLM timeout in seconds")
    reasoning_model_timeout: int = Field(default=120, ge=30, le=300, description="Timeout for reasoning models")

    # Validation
    hypothesis_iterations: int = Field(default=100, ge=10, le=1000, description="Hypothesis test iterations")

    # Ollama (Local Models)
    ollama_api_base: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )

    # Token optimization flags
    use_debate_engine: bool = Field(
        default=False,
        description="Enable LLM debate (expensive)",
    )
    use_local_for_intent: bool = Field(
        default=True,
        description="Use Ollama for intent analysis",
    )
    use_local_for_correction: bool = Field(
        default=True,
        description="Use Ollama for self-correction",
    )

    @property
    def llm_api_keys(self) -> dict[str, str | None]:
        """Return dictionary of all LLM API keys."""
        return {
            "openrouter": self.openrouter_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "kimi": self.kimi_api_key,
            "qwen": self.qwen_api_key,
            "gemini": self.gemini_api_key,
        }

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "*"],
        description="Allowed CORS origins",
    )

    # Debug mode
    debug: bool = Field(default=False, description="Enable debug mode")

    def get_enabled_providers(self) -> list[str]:
        """Return list of providers with configured API keys."""
        return [provider for provider, key in self.llm_api_keys.items() if key is not None]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Module-level singleton for convenience imports
settings = get_settings()


def _export_llm_keys_to_env(s: Settings) -> None:
    """Write LLM API keys from pydantic-settings into os.environ.

    pydantic-settings reads .env into the Settings object but does NOT
    populate os.environ. LiteLLM reads keys directly from os.environ, so
    we bridge the gap here for every configured provider.
    """
    key_map = {
        "GEMINI_API_KEY":     s.gemini_api_key,
        "OPENROUTER_API_KEY": s.openrouter_api_key,
        "OPENAI_API_KEY":     s.openai_api_key,
        "ANTHROPIC_API_KEY":  s.anthropic_api_key,
    }
    for env_var, value in key_map.items():
        if value and not os.environ.get(env_var):
            os.environ[env_var] = value


# Export API keys so LiteLLM can read them at import time
_export_llm_keys_to_env(settings)
