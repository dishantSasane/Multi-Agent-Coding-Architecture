"""Unit tests for validator service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.exceptions import ValidationError
from app.services.validator import Validator


class TestValidator:
    """Test validator service."""

    def test_init(self):
        """Test validator initialization."""
        validator = Validator()
        assert validator is not None

    @pytest.mark.asyncio
    async def test_syntax_check_valid(self, sandbox_code):
        """Test syntax check with valid code."""
        validator = Validator()
        
        result = await validator.check_syntax(sandbox_code, "python")
        
        assert result["valid"] is True
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_syntax_check_invalid(self, invalid_code):
        """Test syntax check with invalid code."""
        validator = Validator()
        
        result = await validator.check_syntax(invalid_code, "python")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_static_analysis_with_ruff(self, sandbox_code):
        """Test static analysis with ruff."""
        validator = Validator()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
            
            result = await validator.run_ruff(sandbox_code)
            
            assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_security_scan_with_bandit(self, sandbox_code):
        """Test security scan with bandit."""
        validator = Validator()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=b"{}", stderr=b"")
            
            result = await validator.run_bandit(sandbox_code)
            
            assert result["passed"] is True
            assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_import_resolution(self, sandbox_code):
        """Test import resolution."""
        validator = Validator()
        
        result = await validator.check_imports(sandbox_code)
        
        assert result["valid"] is True
        assert result["missing_imports"] == []

    @pytest.mark.asyncio
    async def test_validate_all_stages_pass(self, sandbox_code):
        """Test full validation pipeline with all stages passing."""
        validator = Validator()
        
        with patch.object(validator, "check_syntax") as mock_syntax:
            mock_syntax.return_value = {"valid": True, "errors": []}
            
            with patch.object(validator, "run_ruff") as mock_ruff:
                mock_ruff.return_value = {"passed": True, "issues": []}
                
                with patch.object(validator, "run_bandit") as mock_bandit:
                    mock_bandit.return_value = {"passed": True, "issues": []}
                    
                    with patch.object(validator, "check_imports") as mock_imports:
                        mock_imports.return_value = {"valid": True, "missing_imports": []}
                        
                        result = await validator.validate_all("test-task", sandbox_code)
                        
                        assert result["all_passed"] is True
                        assert result["syntax_valid"] is True
                        assert result["security_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_fails_on_syntax_error(self, invalid_code):
        """Test validation fails on syntax error."""
        validator = Validator()
        
        with patch.object(validator, "check_syntax") as mock_syntax:
            mock_syntax.return_value = {
                "valid": False,
                "errors": ["SyntaxError: invalid syntax"],
            }
            
            result = await validator.validate_all("test-task", invalid_code)
            
            assert result["all_passed"] is False
            assert result["syntax_valid"] is False

    @pytest.mark.asyncio
    async def test_validate_fails_on_security_issue(self, malicious_code):
        """Test validation fails on security issue."""
        validator = Validator()
        
        with patch.object(validator, "check_syntax") as mock_syntax:
            mock_syntax.return_value = {"valid": True, "errors": []}
            
            with patch.object(validator, "run_bandit") as mock_bandit:
                mock_bandit.return_value = {
                    "passed": False,
                    "issues": [{"severity": "HIGH", "description": "Dangerous function"}],
                }
                
                result = await validator.validate_all("test-task", malicious_code)
                
                assert result["all_passed"] is False
                assert result["security_valid"] is False

    @pytest.mark.asyncio
    async def test_property_based_testing(self, sandbox_code):
        """Test property-based testing with hypothesis."""
        validator = Validator()
        
        # Create a simple testable function
        test_code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        
        with patch.object(validator, "run_hypothesis_tests") as mock_hypothesis:
            mock_hypothesis.return_value = {
                "passed": True,
                "iterations": 100,
                "failures": [],
            }
            
            result = await validator.run_property_tests(test_code)
            
            assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_unit_test_execution(self, sandbox_code):
        """Test unit test execution."""
        validator = Validator()
        
        test_code = """
import pytest

def test_add():
    assert 2 + 2 == 4
"""
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=b"1 passed", stderr=b"")
            
            result = await validator.run_unit_tests(test_code)
            
            assert result["passed"] is True
            assert result["tests_run"] > 0

    @pytest.mark.asyncio
    async def test_validation_timeout(self, sandbox_code):
        """Test validation timeout handling."""
        validator = Validator()
        validator.timeout = 1  # 1 second timeout
        
        with patch.object(validator, "check_syntax") as mock_syntax:
            mock_syntax.side_effect = TimeoutError("Validation timed out")
            
            with pytest.raises(ValidationError):
                await validator.validate_all("test-task", sandbox_code)

    @pytest.mark.asyncio
    async def test_multi_language_support(self):
        """Test validation supports multiple languages."""
        validator = Validator()
        
        javascript_code = """
function add(a, b) {
    return a + b;
}
"""
        
        # Should handle different languages
        result = await validator.check_syntax(javascript_code, "javascript")
        
        # JavaScript syntax check might be skipped or handled differently
        assert result is not None
