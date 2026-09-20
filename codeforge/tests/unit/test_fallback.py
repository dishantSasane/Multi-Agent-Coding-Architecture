"""Unit tests for FallbackService (app/services/fallback.py)."""

from unittest.mock import AsyncMock

import pytest

from app.core.constants import ModelProvider
from app.core.exceptions import CodeForgeException
from app.services.fallback import FallbackService


class TestFallbackService:
    """Test fallback strategies."""

    def test_init(self):
        """FallbackService wires up a ModelRouterService."""
        service = FallbackService()
        assert service.router is not None

    @pytest.mark.asyncio
    async def test_try_with_fallback_uses_primary_when_it_succeeds(self):
        service = FallbackService()
        primary = AsyncMock(return_value="primary result")
        fallback = AsyncMock(return_value="fallback result")

        result = await service.try_with_fallback(primary, [fallback])

        assert result == "primary result"
        fallback.assert_not_called()

    @pytest.mark.asyncio
    async def test_try_with_fallback_falls_back_on_primary_failure(self):
        service = FallbackService()
        primary = AsyncMock(side_effect=RuntimeError("primary down"))
        fallback = AsyncMock(return_value="fallback result")

        result = await service.try_with_fallback(primary, [fallback])

        assert result == "fallback result"
        fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_with_fallback_raises_when_all_fail(self):
        service = FallbackService()
        primary = AsyncMock(side_effect=RuntimeError("down"))
        fallback = AsyncMock(side_effect=RuntimeError("also down"))

        with pytest.raises(CodeForgeException):
            await service.try_with_fallback(primary, [fallback])

    @pytest.mark.asyncio
    async def test_model_fallback_walks_provider_chain(self):
        service = FallbackService()
        service.router.get_fallback_chain = lambda primary: [ModelProvider.ANTHROPIC]
        service.router.execute_with_model = AsyncMock(
            side_effect=[RuntimeError("openrouter down"), {"content": "ok"}]
        )

        result = await service.model_fallback(
            messages=[{"role": "user", "content": "hi"}],
            preferred_provider=ModelProvider.OPENROUTER,
        )

        assert result == {"content": "ok"}
        assert service.router.execute_with_model.call_count == 2

    @pytest.mark.asyncio
    async def test_model_fallback_raises_when_all_providers_fail(self):
        service = FallbackService()
        service.router.get_fallback_chain = lambda primary: []
        service.router.execute_with_model = AsyncMock(side_effect=RuntimeError("down"))

        with pytest.raises(CodeForgeException):
            await service.model_fallback(
                messages=[{"role": "user", "content": "hi"}],
                preferred_provider=ModelProvider.OPENROUTER,
            )

    @pytest.mark.asyncio
    async def test_strategy_fallback_ensemble_to_single(self):
        service = FallbackService()
        ensemble = AsyncMock(side_effect=RuntimeError("ensemble failed"))
        single = AsyncMock(return_value={"code": "single model result"})

        result = await service.strategy_fallback(ensemble, single)

        assert result == {"code": "single model result"}
        ensemble.assert_called_once()
        single.assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_fallback_to_subprocess(self):
        service = FallbackService()
        docker_exec = AsyncMock(side_effect=RuntimeError("docker unavailable"))
        subprocess_exec = AsyncMock(return_value={"success": True, "exit_code": 0})

        result = await service.sandbox_fallback("print(1)", docker_exec, subprocess_exec)

        assert result["success"] is True
        docker_exec.assert_called_once()
        subprocess_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_fallback_synthetic_failure_without_subprocess(self):
        service = FallbackService()
        docker_exec = AsyncMock(side_effect=RuntimeError("docker unavailable"))

        result = await service.sandbox_fallback("print(1)", docker_exec)

        assert result["success"] is False
        assert "Docker execution failed" in result["stderr"]

    @pytest.mark.asyncio
    async def test_validation_fallback_relaxed_mode(self):
        service = FallbackService()
        strict = AsyncMock(side_effect=RuntimeError("strict failed"))
        relaxed = AsyncMock(return_value={"passed": True, "warnings": ["style"]})

        result, used_relaxed = await service.validation_fallback(strict, relaxed)

        assert used_relaxed is True
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback_uses_alternate_when_open(self):
        service = FallbackService()
        service.router.circuit_breaker.can_execute = AsyncMock(return_value=False)
        service.model_fallback = AsyncMock(return_value={"content": "alt"})

        result = await service.circuit_breaker_fallback(
            ModelProvider.OPENROUTER, [{"role": "user", "content": "hi"}]
        )

        assert result == {"content": "alt"}
        service.model_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback_uses_preferred_when_closed(self):
        service = FallbackService()
        service.router.circuit_breaker.can_execute = AsyncMock(return_value=True)
        service.router.execute_with_model = AsyncMock(return_value={"content": "preferred"})

        result = await service.circuit_breaker_fallback(
            ModelProvider.OPENROUTER, [{"role": "user", "content": "hi"}]
        )

        assert result == {"content": "preferred"}
        service.router.execute_with_model.assert_called_once()


if __name__ == "__main__":
    import asyncio

    async def demo() -> None:
        service = FallbackService()
        assert service.router is not None
        result = await service.try_with_fallback(AsyncMock(return_value="ok"), [])
        assert result == "ok"
        print("self-check passed")

    asyncio.run(demo())
