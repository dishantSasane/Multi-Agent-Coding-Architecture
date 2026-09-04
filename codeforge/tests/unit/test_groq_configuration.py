"""Focused tests for the active Groq LiteLLM configuration."""

import pytest

from app.config import Settings
from app.core.constants import ModelProvider, TASK_TYPE_MODEL_MAP, TaskType
from app.services.model_router import ModelRouterService


def test_groq_key_and_model_load_from_environment(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "qwen/qwen3-32b")

    settings = Settings(_env_file=None)

    assert settings.groq_api_key == "test-groq-key"
    assert settings.groq_model == "qwen/qwen3-32b"
    assert "gemini" not in settings.llm_api_keys


def test_active_task_configuration_selects_groq():
    assert set(TASK_TYPE_MODEL_MAP.values()) == {ModelProvider.GROQ}

    router = ModelRouterService()
    router.settings = Settings(_env_file=None, groq_model="qwen/qwen3-32b")

    assert router.get_optimal_provider(TaskType.IMPLEMENTATION) == ModelProvider.GROQ
    assert router._get_model_for_provider(ModelProvider.GROQ, TaskType.TESTING) == "qwen/qwen3-32b"
    assert router._map_provider_to_litellm(ModelProvider.GROQ, "qwen/qwen3-32b") == (
        "groq/qwen/qwen3-32b"
    )


@pytest.mark.asyncio
async def test_ensemble_default_provider_is_groq(monkeypatch):
    from app.services.ensemble import EnsembleService

    service = EnsembleService()
    captured = []

    async def capture(provider, messages, timeout_seconds):
        captured.append(provider)
        return None

    monkeypatch.setattr(service, "_generate_with_provider", capture)
    await service.generate_ensemble("test", providers=None)

    assert captured
    assert set(captured) == {ModelProvider.GROQ}