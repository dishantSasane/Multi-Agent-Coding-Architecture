"""Unit tests for fallback system."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.exceptions import ModelUnavailableError
from app.models.enums import ModelProvider
from app.services.fallback import FallbackStrategy


class TestFallback:
    """Test fallback system."""

    def test_init(self):
        """Test fallback strategy initialization."""
        strategy = FallbackStrategy()
        assert strategy is not None

    @pytest.mark.asyncio
    async def test_model_fallback_chain(self, sample_model_output):
        """Test fallback through model chain."""
        strategy = FallbackStrategy()
        
        call_order = []
        
        def mock_call(provider, *args, **kwargs):
            call_order.append(provider)
            if provider == ModelProvider.OPENAI:
                raise ModelUnavailableError("OpenAI down")
            return sample_model_output
        
        with patch.object(strategy, "call_model") as mock_model:
            mock_model.side_effect = mock_call
            
            result = await strategy.execute_with_model_fallback(
                prompt="test",
                preferred_models=[ModelProvider.OPENAI, ModelProvider.ANTHROPIC],
            )
            
            assert result is not None
            assert ModelProvider.OPENAI in call_order
            assert ModelProvider.ANTHROPIC in call_order

    @pytest.mark.asyncio
    async def test_strategy_fallback_ensemble_to_single(self):
        """Test fallback from ensemble to single model."""
        strategy = FallbackStrategy()
        
        with patch.object(strategy, "run_ensemble") as mock_ensemble:
            mock_ensemble.side_effect = Exception("Ensemble failed")
            
            with patch.object(strategy, "run_single_model") as mock_single:
                mock_single.return_value = {"code": "single model result"}
                
                result = await strategy.execute_with_strategy_fallback(
                    task_id="test-task",
                    use_ensemble=True,
                )
                
                assert result is not None
                mock_ensemble.assert_called_once()
                mock_single.assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_fallback_to_subprocess(self, sandbox_code):
        """Test fallback from Docker to subprocess."""
        strategy = FallbackStrategy()
        
        with patch.object(strategy, "execute_in_docker") as mock_docker:
            mock_docker.side_effect = Exception("Docker unavailable")
            
            with patch.object(strategy, "execute_in_subprocess") as mock_subprocess:
                mock_subprocess.return_value = {
                    "success": True,
                    "exit_code": 0,
                    "stdout": "5\n",
                }
                
                result = await strategy.execute_with_sandbox_fallback(sandbox_code)
                
                assert result["success"] is True
                mock_docker.assert_called_once()
                mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_fallback_relaxed_mode(self, invalid_code):
        """Test fallback to relaxed validation mode."""
        strategy = FallbackStrategy()
        
        with patch.object(strategy, "validate_strict") as mock_strict:
            mock_strict.return_value = {
                "passed": False,
                "errors": ["Minor style issue"],
            }
            
            with patch.object(strategy, "validate_relaxed") as mock_relaxed:
                mock_relaxed.return_value = {
                    "passed": True,
                    "warnings": ["Style issues ignored"],
                }
                
                result = await strategy.execute_with_validation_fallback(invalid_code)
                
                assert result["passed"] is True
                assert "warnings" in result

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback_queues_job(self):
        """Test that jobs are queued when circuit breaker is open."""
        strategy = FallbackStrategy()
        
        with patch.object(strategy, "is_circuit_open") as mock_circuit:
            mock_circuit.return_value = True
            
            with patch.object(strategy, "queue_for_retry") as mock_queue:
                mock_queue.return_value = {"queued": True, "retry_at": "2024-01-01T00:00:00Z"}
                
                result = await strategy.execute_with_circuit_breaker_fallback(
                    ModelProvider.OPENAI,
                    "test prompt",
                )
                
                assert result["queued"] is True
                mock_queue.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_fallbacks_exhausted_raises_error(self):
        """Test error when all fallbacks are exhausted."""
        strategy = FallbackStrategy()
        
        with patch.object(strategy, "call_model") as mock_model:
            mock_model.side_effect = ModelUnavailableError("All models down")
            
            with pytest.raises(ModelUnavailableError):
                await strategy.execute_with_model_fallback(
                    prompt="test",
                    preferred_models=[ModelProvider.OPENAI, ModelProvider.ANTHROPIC],
                )

    @pytest.mark.asyncio
    async def test_fallback_logs_attempts(self, sample_model_output):
        """Test that fallback attempts are logged."""
        strategy = FallbackStrategy()
        
        call_log = []
        
        def mock_call(provider, *args, **kwargs):
            call_log.append({"provider": provider, "attempt": len(call_log) + 1})
            if provider == ModelProvider.OPENAI:
                raise ModelUnavailableError("First choice down")
            return sample_model_output
        
        with patch.object(strategy, "call_model") as mock_model:
            mock_model.side_effect = mock_call
            
            with patch.object(strategy.logger, "info") as mock_logger:
                result = await strategy.execute_with_model_fallback(
                    prompt="test",
                    preferred_models=[ModelProvider.OPENAI, ModelProvider.ANTHROPIC],
                )
                
                # Logger should have recorded the fallback
                assert mock_logger.call_count >= 1

    def test_get_fallback_priority(self):
        """Test fallback priority ordering."""
        strategy = FallbackStrategy()
        
        # OpenAI should fall back to Anthropic first
        priority = strategy.get_fallback_priority(ModelProvider.OPENAI)
        
        assert ModelProvider.ANTHROPIC in priority
        assert priority.index(ModelProvider.ANTHROPIC) < priority.index(ModelProvider.QWEN)

    @pytest.mark.asyncio
    async def test_graceful_degradation_partial_success(self):
        """Test graceful degradation with partial success."""
        strategy = FallbackStrategy()
        
        results = []
        
        async def mock_parallel_call(provider):
            if provider == ModelProvider.OPENAI:
                raise ModelUnavailableError("Down")
            return {"provider": provider, "code": f"result_{provider}"}
        
        with patch.object(strategy, "call_model_async") as mock_call:
            mock_call.side_effect = mock_parallel_call
            
            providers = [ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.QWEN]
            
            result = await strategy.execute_with_graceful_degradation(providers)
            
            # Should have results from successful providers
            assert len(result["successful"]) == 2
            assert len(result["failed"]) == 1
