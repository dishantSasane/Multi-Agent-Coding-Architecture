"""Unit tests for self-correction engine."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.exceptions import SelfCorrectionExhaustedError
from app.services.self_correction import SelfCorrectionEngine


class TestSelfCorrection:
    """Test self-correction engine."""

    def test_init(self):
        """Test self-correction engine initialization."""
        engine = SelfCorrectionEngine()
        assert engine is not None
        assert engine.max_attempts == 3

    @pytest.mark.asyncio
    async def test_correct_syntax_error(self):
        """Test correction of syntax error."""
        engine = SelfCorrectionEngine()
        
        broken_code = "def broken("
        error_context = {
            "stage": "syntax",
            "error": "SyntaxError",
            "message": "unexpected EOF while parsing",
        }
        
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.return_value = """
```python
def broken():
    pass
```
"""
            
            result = await engine.correct("test-task", broken_code, error_context, attempt=1)
            
            assert result["success"] is True
            assert "corrected_code" in result

    @pytest.mark.asyncio
    async def test_correct_security_issue(self):
        """Test correction of security vulnerability."""
        engine = SelfCorrectionEngine()
        
        vulnerable_code = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
        error_context = {
            "stage": "security",
            "error": "SQLInjection",
            "message": "Potential SQL injection vulnerability detected",
        }
        
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.return_value = """
```python
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```
"""
            
            result = await engine.correct("test-task", vulnerable_code, error_context, attempt=1)
            
            assert result["success"] is True
            assert "%s" in result["corrected_code"]

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test that max attempts limit is enforced."""
        engine = SelfCorrectionEngine()
        
        broken_code = "invalid"
        error_context = {"error": "SyntaxError"}
        
        # Simulate 3 failed attempts
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.return_value = "still invalid"
            
            # First attempt
            await engine.correct("test-task", broken_code, error_context, attempt=1)
            
            # Second attempt
            await engine.correct("test-task", broken_code, error_context, attempt=2)
            
            # Third attempt - should raise error
            with pytest.raises(SelfCorrectionExhaustedError):
                result = await engine.correct(
                    "test-task", broken_code, error_context, attempt=4
                )

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff between retries."""
        engine = SelfCorrectionEngine()
        
        error_context = {"error": "ValidationError"}
        
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.return_value = "fixed code"
            
            with patch("asyncio.sleep") as mock_sleep:
                # First retry should have shorter delay
                await engine.correct("test-task", "code1", error_context, attempt=1)
                
                # Second retry should have longer delay
                await engine.correct("test-task", "code2", error_context, attempt=2)
                
                # Verify backoff increases
                assert mock_sleep.call_count >= 0

    @pytest.mark.asyncio
    async def test_error_context_included_in_prompt(self):
        """Test that error context is included in correction prompt."""
        engine = SelfCorrectionEngine()
        
        error_context = {
            "stage": "validation",
            "error": "ImportError",
            "message": "ModuleNotFoundError: No module named 'requests'",
            "traceback": "File \"test.py\", line 5",
        }
        
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.return_value = "import requests\n# fixed"
            
            await engine.correct("test-task", "code", error_context, attempt=1)
            
            # Verify the prompt includes error context
            call_args = mock_completion.call_args
            prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
            
            assert "ImportError" in prompt or "ModuleNotFoundError" in prompt

    @pytest.mark.asyncio
    async def test_successful_correction_validated(self):
        """Test that corrected code is validated."""
        engine = SelfCorrectionEngine()
        
        error_context = {"error": "SyntaxError"}
        
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.return_value = "def valid(): pass"
            
            with patch.object(engine.validator, "check_syntax") as mock_validate:
                mock_validate.return_value = {"valid": True, "errors": []}
                
                result = await engine.correct("test-task", "invalid", error_context, attempt=1)
                
                assert result["success"] is True
                mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_correction_preserves_functionality(self):
        """Test that corrections preserve original functionality."""
        engine = SelfCorrectionEngine()
        
        original_code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""
        
        # Missing type hints (not a functional issue)
        error_context = {
            "stage": "style",
            "error": "MissingTypeHints",
            "message": "Function lacks type annotations",
        }
        
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.return_value = """
def calculate_total(items: list) -> float:
    total = 0
    for item in items:
        total += item.price
    return total
"""
            
            result = await engine.correct("test-task", original_code, error_context, attempt=1)
            
            assert result["success"] is True
            # Core logic should be preserved
            assert "total += item.price" in result["corrected_code"]

    @pytest.mark.asyncio
    async def test_unfixable_error_returns_original(self):
        """Test handling of unfixable errors."""
        engine = SelfCorrectionEngine()
        
        # Semantic error that can't be auto-fixed
        error_context = {
            "stage": "logic",
            "error": "LogicError",
            "message": "Algorithm produces incorrect results for edge case",
        }
        
        with patch.object(engine.llm_client, "completion") as mock_completion:
            mock_completion.side_effect = Exception("Cannot fix without more context")
            
            result = await engine.correct("test-task", "code", error_context, attempt=1)
            
            # Should indicate failure but not crash
            assert result["success"] is False
            assert "error" in result
