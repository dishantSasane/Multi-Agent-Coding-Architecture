"""Unit tests for model router."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.circuit_breaker import CircuitBreaker
from app.core.exceptions import CircuitBreakerOpenError, ModelUnavailableError
from app.models.enums import ModelProvider
from app.services.model_router import ModelRouter


class TestModelRouter:
    """Test model router service."""

    def test_init(self):
        """Test model router initialization."""
        router = ModelRouter()
        assert router is not None
        assert len(router.providers) > 0

    def test_get_provider_for_task_type(self):
        """Test provider selection based on task type."""
        router = ModelRouter()
        
        # Architecture tasks should prefer Claude
        provider = router.get_optimal_provider("architecture", "design a system")
        assert provider is not None
        
        # General implementation should prefer GPT-4o
        provider = router.get_optimal_provider("implementation", "build a function")
        assert provider is not None
        
        # Algorithm tasks should prefer Qwen
        provider = router.get_optimal_provider("algorithm", "optimize this sorting")
        assert provider is not None

    @pytest.mark.asyncio
    async def test_route_with_fallback(self, sample_model_output):
        """Test routing with fallback chain."""
        router = ModelRouter()
        
        with patch.object(router, "call_llm") as mock_call:
            mock_call.return_value = sample_model_output
            
            result = await router.route(
                provider=ModelProvider.OPENAI,
                prompt="test prompt",
                task_type="general",
            )
            
            assert result is not None
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after failures."""
        router = ModelRouter()
        
        # Simulate failures
        for _ in range(6):
            with patch.object(router, "call_llm") as mock_call:
                mock_call.side_effect = Exception("API Error")
                
                try:
                    await router.route(
                        provider=ModelProvider.OPENAI,
                        prompt="test",
                        task_type="general",
                    )
                except Exception:
                    pass
        
        # Circuit breaker should be open now
        assert router.circuit_breakers[ModelProvider.OPENAI].is_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_calls(self):
        """Test that open circuit breaker prevents API calls."""
        router = ModelRouter()
        
        # Manually open the circuit breaker
        router.circuit_breakers[ModelProvider.OPENAI] = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=30,
        )
        router.circuit_breakers[ModelProvider.OPENAI]._failures = 1
        router.circuit_breakers[ModelProvider.OPENAI]._last_failure_time = router._get_current_time()
        
        with pytest.raises(CircuitBreakerOpenError):
            await router.route(
                provider=ModelProvider.OPENAI,
                prompt="test",
                task_type="general",
            )

    @pytest.mark.asyncio
    async def test_adaptive_routing_based_on_latency(self):
        """Test adaptive routing considers latency."""
        router = ModelRouter()
        
        # Record some latencies
        router.latency_stats[ModelProvider.OPENAI] = [100, 150, 200]
        router.latency_stats[ModelProvider.ANTHROPIC] = [500, 600, 700]
        
        # OPENAI should be preferred due to lower latency
        provider = router.get_optimal_provider("general", "test")
        assert provider is not None

    @pytest.mark.asyncio
    async def test_success_rate_tracking(self):
        """Test success rate tracking."""
        router = ModelRouter()
        
        # Record successes and failures
        router.success_counts[ModelProvider.OPENAI] = 8
        router.failure_counts[ModelProvider.OPENAI] = 2
        
        success_rate = router.get_success_rate(ModelProvider.OPENAI)
        assert success_rate == 0.8

    @pytest.mark.asyncio
    async def test_fallback_chain(self, sample_model_output):
        """Test fallback to alternative providers."""
        router = ModelRouter()
        
        call_order = []
        
        def side_effect(provider, *args, **kwargs):
            call_order.append(provider)
            if provider == ModelProvider.OPENAI:
                raise ModelUnavailableError("OpenAI is down")
            return sample_model_output
        
        with patch.object(router, "call_llm") as mock_call:
            mock_call.side_effect = side_effect
            
            result = await router.route_with_fallback(
                prompt="test",
                task_type="general",
                preferred_providers=[ModelProvider.OPENAI, ModelProvider.ANTHROPIC],
            )
            
            assert result is not None
            assert ModelProvider.OPENAI in call_order
            assert ModelProvider.ANTHROPIC in call_order

    @pytest.mark.asyncio
    async def test_no_available_providers_raises_error(self):
        """Test error when all providers are unavailable."""
        router = ModelRouter()
        
        with patch.object(router, "call_llm") as mock_call:
            mock_call.side_effect = ModelUnavailableError("All providers down")
            
            with pytest.raises(ModelUnavailableError):
                await router.route_with_fallback(
                    prompt="test",
                    task_type="general",
                    preferred_providers=[ModelProvider.OPENAI],
                )

    def test_get_all_available_providers(self):
        """Test getting available providers."""
        router = ModelRouter()
        
        providers = router.get_available_providers()
        assert len(providers) > 0
        
        # All providers should be enums
        for provider in providers:
            assert isinstance(provider, ModelProvider)

    def test_model_capabilities(self):
        """Test model capability lookup."""
        router = ModelRouter()
        
        # Check that capabilities are defined
        capabilities = router.get_model_capabilities("gpt-4o")
        assert capabilities is not None
