"""Model Router Service - Route tasks to optimal LLM providers."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import structlog
from litellm import acompletion

from app.config import get_settings
from app.core.circuit_breaker import get_circuit_breaker
from app.core.constants import (
    DEFAULT_MODEL_TIMEOUT,
    PROVIDER_MODELS,
    REASONING_MODEL_TIMEOUT,
    TASK_TYPE_MODEL_MAP,
)
from app.core.exceptions import CircuitBreakerOpenError, ModelUnavailableError
from app.models.enums import ModelProvider, TaskType

logger = structlog.get_logger(__name__)


@dataclass
class ModelStats:
    """Statistics for a model."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency_ms: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0


class ModelRouterService:
    """Service for routing tasks to optimal LLM providers."""

    def __init__(self) -> None:
        """Initialize model router service."""
        self.settings = get_settings()
        self.circuit_breaker = get_circuit_breaker()
        self._model_stats: dict[str, ModelStats] = defaultdict(ModelStats)
        self._provider_priority: dict[ModelProvider, int] = {
            ModelProvider.ANTHROPIC: 1,
            ModelProvider.OPENAI: 2,
            ModelProvider.QWEN: 3,
            ModelProvider.GEMINI: 4,
            ModelProvider.KIMI: 5,
        }

    def _get_model_for_provider(self, provider: ModelProvider) -> str:
        """Get the best model name for a provider."""
        models = PROVIDER_MODELS.get(provider, [])
        if not models:
            raise ModelUnavailableError(
                provider=provider.value,
                model="unknown",
                details={"reason": "No models configured for provider"},
            )
        return models[0]  # Return primary model

    def _map_provider_to_litellm(self, provider: ModelProvider, model: str) -> str:
        """Map provider and model to LiteLLM format."""
        provider_model_map = {
            ModelProvider.OPENAI: f"openai/{model}",
            ModelProvider.ANTHROPIC: f"anthropic/{model}",
            ModelProvider.KIMI: f"kimi/{model}",
            ModelProvider.QWEN: f"qwen/{model}",
            ModelProvider.GEMINI: f"gemini/{model}",
        }
        return provider_model_map.get(provider, f"{provider.value}/{model}")

    def get_optimal_provider(self, task_type: TaskType) -> ModelProvider:
        """Get the optimal provider for a task type.

        Args:
            task_type: The type of task.

        Returns:
            Optimal provider for the task.
        """
        # Get default provider for task type
        default_provider = TASK_TYPE_MODEL_MAP.get(task_type, ModelProvider.OPENAI)

        # Check if circuit breaker is open
        if not self.circuit_breaker.can_execute(default_provider.value):
            logger.warning(
                "circuit_breaker_open_fallback",
                provider=default_provider.value,
                task_type=task_type.value,
            )
            # Fallback to next available provider
            return self._get_fallback_provider(default_provider)

        return default_provider

    def _get_fallback_provider(self, excluded: ModelProvider) -> ModelProvider:
        """Get fallback provider excluding the given one.

        Args:
            excluded: Provider to exclude.

        Returns:
            Next best available provider.
        """
        sorted_providers = sorted(
            [p for p in ModelProvider if p != excluded],
            key=lambda p: self._provider_priority.get(p, 99),
        )

        for provider in sorted_providers:
            if self.circuit_breaker.can_execute(provider.value):
                return provider

        # If all circuits are open, return the first one anyway
        return sorted_providers[0] if sorted_providers else ModelProvider.OPENAI

    async def execute_with_model(
        self,
        provider: ModelProvider,
        messages: list[dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute a completion with a specific model.

        Args:
            provider: The provider to use.
            messages: List of message dicts.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.

        Returns:
            Response dictionary with content and metadata.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open.
            ModelUnavailableError: If model is unavailable.
        """
        # Check circuit breaker
        await self.circuit_breaker.check_and_raise(provider.value)

        model_name = self._get_model_for_provider(provider)
        litellm_model = self._map_provider_to_litellm(provider, model_name)

        # Determine timeout
        if timeout is None:
            timeout = (
                REASONING_MODEL_TIMEOUT
                if provider in [ModelProvider.ANTHROPIC, ModelProvider.OPENAI]
                else DEFAULT_MODEL_TIMEOUT
            )

        start_time = time.time()
        stats_key = f"{provider.value}:{model_name}"

        try:
            response = await acompletion(
                model=litellm_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                request_timeout=timeout,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Record success
            await self.circuit_breaker.record_success(provider.value)
            self._update_stats(stats_key, success=True, latency_ms=latency_ms)

            content = response.choices[0].message.content or ""
            usage = response.usage if hasattr(response, "usage") else None

            return {
                "success": True,
                "content": content,
                "provider": provider.value,
                "model": model_name,
                "latency_ms": latency_ms,
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            # Record failure
            await self.circuit_breaker.record_failure(provider.value, error_msg)
            self._update_stats(stats_key, success=False, latency_ms=latency_ms)

            logger.exception(
                "model_execution_failed",
                provider=provider.value,
                model=model_name,
                error=error_msg,
            )

            raise ModelUnavailableError(
                provider=provider.value,
                model=model_name,
                details={"error": error_msg},
            )

    def _update_stats(self, model_key: str, success: bool, latency_ms: int) -> None:
        """Update model statistics.

        Args:
            model_key: Model identifier.
            success: Whether the call was successful.
            latency_ms: Call latency in milliseconds.
        """
        stats = self._model_stats[model_key]
        stats.total_calls += 1

        if success:
            stats.successful_calls += 1
        else:
            stats.failed_calls += 1

        stats.total_latency_ms += latency_ms
        stats.avg_latency_ms = stats.total_latency_ms / stats.total_calls
        stats.success_rate = stats.successful_calls / stats.total_calls

    def get_model_stats(self, provider: ModelProvider | None = None) -> dict[str, Any]:
        """Get statistics for models.

        Args:
            provider: Optional provider to filter by.

        Returns:
            Dictionary of model statistics.
        """
        if provider:
            key_prefix = f"{provider.value}:"
            stats = {
                k: vars(v) for k, v in self._model_stats.items() if k.startswith(key_prefix)
            }
        else:
            stats = {k: vars(v) for k, v in self._model_stats.items()}

        return {"models": stats, "circuit_breakers": {}}

    def get_fallback_chain(self, primary: ModelProvider) -> list[ModelProvider]:
        """Get fallback chain for a provider.

        Args:
            primary: Primary provider.

        Returns:
            List of fallback providers in order.
        """
        fallbacks = [p for p in ModelProvider if p != primary]
        return sorted(fallbacks, key=lambda p: self._provider_priority.get(p, 99))
