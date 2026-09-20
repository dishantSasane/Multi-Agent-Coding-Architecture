"""Unit tests for SelfCorrectionService (app/services/self_correction.py)."""

from unittest.mock import AsyncMock

import pytest
from tenacity import RetryError

from app.core.constants import ModelProvider
from app.models.models import ValidationResult
from app.services.self_correction import SelfCorrectionService


def _result(stage: str, passed: bool, errors: list[str] | None = None) -> ValidationResult:
    return ValidationResult(stage=stage, passed=passed, errors=errors or [])


class TestSelfCorrectionService:
    """Test self-correction service."""

    def test_init(self):
        service = SelfCorrectionService()
        assert service is not None
        assert "Fix ALL the validation errors" in service.correction_prompt

    @pytest.mark.asyncio
    async def test_correct_code_returns_unchanged_when_all_passed(self):
        service = SelfCorrectionService()
        results = [_result("syntax", passed=True)]

        corrected = await service.correct_code("print(1)", results, requirements=[])

        assert corrected == "print(1)"

    @pytest.mark.asyncio
    async def test_correct_code_calls_llm_with_errors(self):
        service = SelfCorrectionService()
        service.router.execute_with_model = AsyncMock(
            return_value={"content": "```python\ndef fixed(): pass\n```"}
        )
        results = [_result("syntax", passed=False, errors=["unexpected EOF"])]

        corrected = await service.correct_code(
            "def broken(", results, requirements=["Fix syntax"]
        )

        assert corrected == "def fixed(): pass"
        service.router.execute_with_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_correct_code_uses_requested_provider(self):
        service = SelfCorrectionService()
        service.router.execute_with_model = AsyncMock(return_value={"content": "fixed"})
        results = [_result("syntax", passed=False, errors=["bad"])]

        await service.correct_code(
            "code", results, requirements=[], provider=ModelProvider.GROQ.value
        )

        call_kwargs = service.router.execute_with_model.call_args[1]
        assert call_kwargs["provider"] == ModelProvider.GROQ

    @pytest.mark.asyncio
    async def test_correct_code_propagates_llm_failure(self):
        service = SelfCorrectionService()
        service.router.execute_with_model = AsyncMock(side_effect=RuntimeError("provider down"))
        results = [_result("syntax", passed=False, errors=["bad"])]

        # @retry(stop_after_attempt(3)) wraps the exhausted failure in a
        # tenacity.RetryError rather than re-raising the original error.
        with pytest.raises(RetryError):
            await service.correct_code("code", results, requirements=[])

    @pytest.mark.asyncio
    async def test_run_correction_loop_succeeds_first_try(self):
        service = SelfCorrectionService()
        validate_func = AsyncMock(return_value=[_result("syntax", passed=True)])

        final_code, results, success = await service.run_correction_loop(
            "print(1)", None, validate_func, max_attempts=3
        )

        assert success is True
        assert final_code == "print(1)"
        validate_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_correction_loop_corrects_then_succeeds(self):
        service = SelfCorrectionService()
        validate_func = AsyncMock(
            side_effect=[
                [_result("syntax", passed=False, errors=["bad"])],
                [_result("syntax", passed=True)],
            ]
        )
        service.correct_code = AsyncMock(return_value="print('fixed')")

        final_code, results, success = await service.run_correction_loop(
            "broken(", None, validate_func, max_attempts=3
        )

        assert success is True
        assert final_code == "print('fixed')"
        assert validate_func.call_count == 2
        service.correct_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_correction_loop_exhausts_attempts(self):
        service = SelfCorrectionService()
        validate_func = AsyncMock(return_value=[_result("syntax", passed=False, errors=["bad"])])
        service.correct_code = AsyncMock(return_value="still broken")

        final_code, results, success = await service.run_correction_loop(
            "broken(", None, validate_func, max_attempts=2
        )

        assert success is False
        assert validate_func.call_count == 2

    @pytest.mark.asyncio
    async def test_run_correction_loop_stops_when_correction_fails(self):
        service = SelfCorrectionService()
        validate_func = AsyncMock(return_value=[_result("syntax", passed=False, errors=["bad"])])
        service.correct_code = AsyncMock(side_effect=RuntimeError("llm down"))

        final_code, results, success = await service.run_correction_loop(
            "broken(", None, validate_func, max_attempts=3
        )

        assert success is False
        # correction attempted once, then loop bails rather than retrying blindly
        service.correct_code.assert_called_once()

    def test_format_error_context(self):
        service = SelfCorrectionService()
        results = [
            _result("syntax", passed=False, errors=["unexpected EOF"]),
            _result("security", passed=True),
        ]

        context = service.format_error_context(results)

        assert "### syntax" in context
        assert "unexpected EOF" in context
        assert "### security" not in context


if __name__ == "__main__":
    import asyncio

    async def demo() -> None:
        service = SelfCorrectionService()
        service.router.execute_with_model = AsyncMock(return_value={"content": "print(1)"})
        results = [_result("syntax", passed=False, errors=["bad"])]
        corrected = await service.correct_code("broken(", results, requirements=[])
        assert corrected == "print(1)"
        print("self-check passed")

    asyncio.run(demo())
