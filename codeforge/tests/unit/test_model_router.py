"""Unit tests for ModelRouterService (app/services/model_router.py)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.circuit_breaker import CircuitBreaker
from app.core.constants import ModelProvider, TaskType
from app.core.exceptions import ModelUnavailableError
from app.services.model_router import ModelRouterService


def _llm_response(content: str = "ok") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=None,
    )


def _isolated_router() -> ModelRouterService:
    """ModelRouterService.__init__ pulls in get_circuit_breaker(), a
    process-wide singleton (app/core/circuit_breaker.py) — so state tripped
    by one test file leaks into the next. Swap in a fresh instance so each
    test starts from a clean circuit.
    """
    router = ModelRouterService()
    router.circuit_breaker = CircuitBreaker(
        failure_threshold=router.circuit_breaker.failure_threshold,
        recovery_timeout=router.circuit_breaker.recovery_timeout,
    )
    return router


class TestModelRouterService:
    """Test model router service."""

    def test_init(self):
        router = _isolated_router()
        assert router is not None
        assert len(router._provider_priority) > 0

    @pytest.mark.asyncio
    async def test_get_optimal_provider_returns_task_default(self):
        router = _isolated_router()

        provider = await router.get_optimal_provider(TaskType.ARCHITECTURE)
        assert isinstance(provider, ModelProvider)

    @pytest.mark.asyncio
    async def test_get_optimal_provider_falls_back_when_circuit_open(self):
        router = _isolated_router()
        default_provider = await router.get_optimal_provider(TaskType.ARCHITECTURE)

        # Trip the circuit for whichever provider is the task default.
        for _ in range(router.circuit_breaker.failure_threshold):
            await router.circuit_breaker.record_failure(default_provider.value)

        fallback = await router.get_optimal_provider(TaskType.ARCHITECTURE)
        assert fallback != default_provider

    @pytest.mark.asyncio
    async def test_execute_with_model_success(self):
        router = _isolated_router()

        with patch(
            "app.services.model_router.acompletion",
            AsyncMock(return_value=_llm_response("generated code")),
        ):
            result = await router.execute_with_model(
                provider=ModelProvider.GROQ,
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result["success"] is True
        assert result["content"] == "generated code"

    @pytest.mark.asyncio
    async def test_execute_with_model_raises_model_unavailable_on_failure(self):
        router = _isolated_router()

        with patch(
            "app.services.model_router.acompletion",
            AsyncMock(side_effect=RuntimeError("provider down")),
        ):
            with pytest.raises(ModelUnavailableError):
                await router.execute_with_model(
                    provider=ModelProvider.GROQ,
                    messages=[{"role": "user", "content": "hi"}],
                )

    @pytest.mark.asyncio
    async def test_execute_with_model_records_circuit_breaker_failure(self):
        router = _isolated_router()

        with patch(
            "app.services.model_router.acompletion",
            AsyncMock(side_effect=RuntimeError("provider down")),
        ):
            with pytest.raises(ModelUnavailableError):
                await router.execute_with_model(
                    provider=ModelProvider.GROQ,
                    messages=[{"role": "user", "content": "hi"}],
                )

        stats = await router.circuit_breaker.get_stats(ModelProvider.GROQ.value)
        assert stats["failure_count"] == 1

    def test_get_fallback_chain_excludes_primary(self):
        router = _isolated_router()

        chain = router.get_fallback_chain(ModelProvider.OPENROUTER)

        assert ModelProvider.OPENROUTER not in chain
        assert len(chain) == len(list(ModelProvider)) - 1

    def test_model_stats_track_success_and_failure(self):
        router = _isolated_router()

        router._update_stats("groq:model", success=True, latency_ms=100)
        router._update_stats("groq:model", success=False, latency_ms=200)

        stats = router.get_model_stats(ModelProvider.GROQ)["models"]["groq:model"]
        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 1
        assert stats["success_rate"] == 0.5


if __name__ == "__main__":
    import asyncio

    async def demo() -> None:
        router = _isolated_router()
        with patch(
            "app.services.model_router.acompletion",
            AsyncMock(return_value=_llm_response("ok")),
        ):
            result = await router.execute_with_model(
                provider=ModelProvider.GROQ, messages=[{"role": "user", "content": "hi"}]
            )
            assert result["success"] is True
        print("self-check passed")

    asyncio.run(demo())


@pytest.mark.asyncio
async def test_openrouter_walks_free_pool_on_rate_limit():
    """A 429 on the first free model moves to the next; only :free slugs are used."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from litellm.exceptions import RateLimitError

    from app.core.constants import OPENROUTER_FREE_POOL, ModelProvider
    from app.services.model_router import ModelRouterService

    assert all(m.endswith(":free") for m in OPENROUTER_FREE_POOL)
    ok = MagicMock()
    ok.choices = [MagicMock(message=MagicMock(content="hi"))]
    ok.usage = None
    router = ModelRouterService()
    await router.circuit_breaker.reset()
    mock = AsyncMock(side_effect=[RateLimitError("busy", "openrouter", "m"), ok])
    with patch("app.services.model_router.acompletion", mock):
        result = await router.execute_with_model(
            ModelProvider.OPENROUTER, [{"role": "user", "content": "x"}]
        )
    assert result["model"] == OPENROUTER_FREE_POOL[1]
    assert mock.call_count == 2


@pytest.mark.asyncio
async def test_truncated_output_is_rejected():
    """finish_reason=length means a cut-off project; the member must fail, not validate."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.core.constants import ModelProvider
    from app.core.exceptions import ModelUnavailableError
    from app.services.model_router import ModelRouterService

    cut = MagicMock()
    cut.choices = [MagicMock(finish_reason="length", message=MagicMock(content="def f("))]
    cut.usage = None
    router = ModelRouterService()
    await router.circuit_breaker.reset()
    with patch("app.services.model_router.acompletion", AsyncMock(return_value=cut)):
        with pytest.raises(ModelUnavailableError):
            await router.execute_with_model(ModelProvider.GROQ, [{"role": "user", "content": "x"}])
    await router.circuit_breaker.reset()
