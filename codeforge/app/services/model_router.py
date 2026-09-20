"""Model Router Service - Route tasks to optimal LLM providers."""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from litellm import acompletion
from litellm.exceptions import NotFoundError, RateLimitError, ServiceUnavailableError

from app.config import get_settings
from app.core.circuit_breaker import get_circuit_breaker
from app.core.constants import (
    DEFAULT_MODEL_TIMEOUT,
    OPENROUTER_FREE_POOL,
    OPENROUTER_TASK_MODEL_MAP,
    PROVIDER_MODELS,
    REASONING_MODEL_TIMEOUT,
    TASK_TYPE_MODEL_MAP,
    ModelProvider,
    TaskType,
)
from app.core.exceptions import ModelUnavailableError

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
            ModelProvider.GROQ: 1,
            ModelProvider.OPENROUTER: 2,
            ModelProvider.GEMINI: 2,
            ModelProvider.ANTHROPIC: 3,
            ModelProvider.OPENAI: 4,
            ModelProvider.QWEN: 5,
            ModelProvider.KIMI: 6,
        }
        
        # Ollama client (for free local inference)
        self.ollama_base = self.settings.ollama_api_base
        self.ollama_client = httpx.AsyncClient(
            base_url=self.ollama_base,
            timeout=120.0,
        )
        
        # Cost tier routing
        self.cloud_models = {
            ModelProvider.QWEN: "qwen/qwen-2.5-coder-32b-instruct",
            ModelProvider.KIMI: "moonshotai/kimi-k2-72b",
        }
        self.local_models = {
            ModelProvider.QWEN: "qwen2.5-coder:7b",
            ModelProvider.KIMI: "mistral:7b",  # Fallback if Kimi not available locally
        }

    def _get_model_for_provider(
        self, provider: ModelProvider, task_type: TaskType | None = None
    ) -> str:
        """Get the best model name for a provider.

        For OPENROUTER, picks the task-specific free-tier model when a
        ``task_type`` is supplied; falls back to the primary list entry.
        """
        if provider == ModelProvider.GROQ:
            return self.settings.groq_model

        if provider == ModelProvider.OPENROUTER and task_type is not None:
            return OPENROUTER_TASK_MODEL_MAP.get(task_type, "free")

        models = PROVIDER_MODELS.get(provider, [])
        if not models:
            raise ModelUnavailableError(
                provider=provider.value,
                model="unknown",
                details={"reason": "No models configured for provider"},
            )
        return models[0]  # Return primary model

    def _map_provider_to_litellm(self, provider: ModelProvider, model: str) -> str:
        """Map provider and model to LiteLLM format.

        OpenRouter free-tier models are addressed as ``openrouter/<full-slug>``.
        LiteLLM reads OPENROUTER_API_KEY from the environment automatically.
        """
        if provider == ModelProvider.OPENROUTER:
            # LiteLLM OpenRouter prefix: openrouter/<model-slug>
            # e.g. openrouter/poolside/laguna-m.1:free
            return f"openrouter/{model}"

        provider_model_map = {
            ModelProvider.OPENAI: f"openai/{model}",
            ModelProvider.ANTHROPIC: f"anthropic/{model}",
            ModelProvider.KIMI: f"kimi/{model}",
            ModelProvider.QWEN: f"qwen/{model}",
            ModelProvider.GROQ: f"groq/{model}",
        }
        return provider_model_map.get(provider, f"{provider.value}/{model}")

    async def get_optimal_provider(self, task_type: TaskType) -> ModelProvider:
        """Get the optimal provider for a task type.

        Args:
            task_type: The type of task.

        Returns:
            Optimal provider for the task.
        """
        # Get default provider for task type
        default_provider = TASK_TYPE_MODEL_MAP.get(task_type, ModelProvider.OPENAI)

        # Check if circuit breaker is open
        if not await self.circuit_breaker.can_execute(default_provider.value):
            logger.warning(
                "circuit_breaker_open_fallback",
                provider=default_provider.value,
                task_type=task_type.value,
            )
            # Fallback to next available provider
            return await self._get_fallback_provider(default_provider)

        return default_provider

    async def _get_fallback_provider(self, excluded: ModelProvider) -> ModelProvider:
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
            if await self.circuit_breaker.can_execute(provider.value):
                return provider

        # If all circuits are open, return the first one anyway
        return sorted_providers[0] if sorted_providers else ModelProvider.OPENAI

    async def execute_with_model(
        self,
        provider: ModelProvider,
        messages: list[dict[str, str]],
        max_tokens: int = 6500,  # Groq free tier: prompt + max_tokens must stay under 8000 TPM
        temperature: float = 0.7,
        timeout: int | None = None,
        use_local: bool = False,
        task_type: TaskType | None = None,
    ) -> dict[str, Any]:
        """Execute a completion with a specific model.

        Args:
            provider: The provider to use.
            messages: List of message dicts.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.
            use_local: If True, use local Ollama model.

        Returns:
            Response dictionary with content and metadata.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open.
            ModelUnavailableError: If model is unavailable.
        """
        # Use local model if requested
        if use_local:
            return await self._call_ollama(provider, messages, max_tokens, temperature)
        
        # Check circuit breaker for cloud models
        await self.circuit_breaker.check_and_raise(provider.value)

        model_name = self._get_model_for_provider(provider, task_type)
        # Determine timeout — Groq, Anthropic and OpenAI all need the longer
        # 120-second window for code generation tasks.
        if timeout is None:
            timeout = (
                REASONING_MODEL_TIMEOUT
                if provider in [ModelProvider.GROQ, ModelProvider.ANTHROPIC, ModelProvider.OPENAI,
                            ModelProvider.OPENROUTER, ModelProvider.GEMINI]
                else DEFAULT_MODEL_TIMEOUT
            )

        start_time = time.time()
        stats_key = f"{provider.value}:{model_name}"

        try:
            # OpenRouter: walk the free pool on 429/503. Other providers: one model.
            candidates = OPENROUTER_FREE_POOL if provider == ModelProvider.OPENROUTER else [model_name]
            for i, model_name in enumerate(candidates):
                try:
                    response = await acompletion(
                        model=self._map_provider_to_litellm(provider, model_name),
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        request_timeout=timeout,
                        num_retries=2,  # same-model retry on 429/503
                    )
                    break
                except (RateLimitError, ServiceUnavailableError, NotFoundError):
                    if i == len(candidates) - 1:
                        raise
                    logger.warning("free_model_busy_trying_next", model=model_name)
            stats_key = f"{provider.value}:{model_name}"

            latency_ms = int((time.time() - start_time) * 1000)

            # Record success
            await self.circuit_breaker.record_success(provider.value)
            self._update_stats(stats_key, success=True, latency_ms=latency_ms)

            content = response.choices[0].message.content or ""
            if getattr(response.choices[0], "finish_reason", None) == "length":
                # Cut off mid-file: better to drop this member than validate half a project.
                raise ModelUnavailableError(
                    provider=provider.value,
                    model=model_name,
                    details={"error": "output truncated (finish_reason=length)"},
                )
            usage = response.usage if hasattr(response, "usage") else None
            logger.info(
                "model_call_ok",
                provider=provider.value,
                model=model_name,
                prompt_tokens=usage.prompt_tokens if usage else None,
                latency_ms=latency_ms,
            )

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

    async def _call_ollama(
        self,
        provider: ModelProvider,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Call local Ollama model.

        Args:
            provider: The provider to use (determines which local model).
            messages: List of message dicts.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Response dictionary with content and metadata.
        """
        model_id = self.local_models.get(provider, "qwen2.5-coder:7b")
        start_time = time.time()
        
        try:
            # Extract system and user messages
            system_prompt = ""
            user_prompt = ""
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                elif msg["role"] == "user":
                    user_prompt = msg["content"]
            
            response = await self.ollama_client.post(
                "/api/generate",
                json={
                    "model": model_id,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            response.raise_for_status()
            data = response.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "content": data.get("response", ""),
                "provider": f"ollama:{provider.value}",
                "model": model_id,
                "latency_ms": latency_ms,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            }
            
        except Exception as e:
            logger.warning("ollama_failed", error=str(e))
            # Fallback to cloud if local fails
            # Re-call with use_local=False to use cloud
            return await self.execute_with_model(
                provider=provider,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                use_local=False,
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
