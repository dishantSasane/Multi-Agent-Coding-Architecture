"""Self-Correction Service - Automatic error correction loop."""

import asyncio
from typing import Any

import structlog
from litellm import acompletion
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import SelfCorrectionExhaustedError
from app.models.models import ValidationResult
from app.services.model_router import ModelRouterService
from app.models.enums import ModelProvider

logger = structlog.get_logger(__name__)


class SelfCorrectionService:
    """Service for automatic code correction based on validation errors."""

    def __init__(self) -> None:
        """Initialize self-correction service."""
        self.router = ModelRouterService()
        self.correction_prompt = self._load_correction_prompt()

    def _load_correction_prompt(self) -> str:
        """Load the correction prompt template."""
        return """You are an expert developer fixing code issues.

Original Code:
```python
{original_code}
```

Validation Errors:
{errors}

Task Requirements:
{requirements}

Fix ALL the validation errors while maintaining the original functionality.
Output ONLY the corrected complete code, no explanations.
Ensure:
- All syntax errors are fixed
- No security vulnerabilities remain
- All imports are valid
- Code follows best practices

Corrected Code:"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def correct_code(
        self,
        original_code: str,
        validation_results: list[ValidationResult],
        requirements: list[str],
        provider: str | None = None,
    ) -> str:
        """Attempt to correct code based on validation errors.

        Args:
            original_code: The code that failed validation.
            validation_results: Results from validation pipeline.
            requirements: Original task requirements.
            provider: Optional provider to use for correction.

        Returns:
            Corrected code string.

        Raises:
            SelfCorrectionExhaustedError: If correction fails after retries.
        """
        # Collect all errors
        errors = []
        for result in validation_results:
            if not result.passed:
                errors.append(f"**{result.stage}**:\n" + "\n".join(result.errors))

        if not errors:
            return original_code

        error_summary = "\n\n".join(errors)

        prompt = self.correction_prompt.format(
            original_code=original_code,
            errors=error_summary,
            requirements="\n".join(f"- {r}" for r in requirements),
        )

        try:
            result = await self.router.execute_with_model(
                provider=ModelProvider(provider) if provider else ModelProvider.OPENAI,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.3,  # Lower temperature for fixes
            )

            corrected_code = result["content"]

            # Extract code from response
            import re

            code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", corrected_code, re.DOTALL)
            if code_blocks:
                corrected_code = max(code_blocks, key=len).strip()

            logger.info(
                "code_corrected",
                original_length=len(original_code),
                corrected_length=len(corrected_code),
            )

            return corrected_code

        except Exception as e:
            logger.exception("correction_failed", error=str(e))
            raise

    async def run_correction_loop(
        self,
        code: str,
        test_code: str | None,
        validate_func: Any,
        max_attempts: int = 3,
    ) -> tuple[str, list[ValidationResult], bool]:
        """Run correction loop until validation passes or max attempts reached.

        Args:
            code: Initial code to validate and correct.
            test_code: Optional test code.
            validate_func: Async function to validate code.
            max_attempts: Maximum correction attempts.

        Returns:
            Tuple of (final_code, validation_results, success).
        """
        current_code = code
        last_errors = []

        for attempt in range(max_attempts):
            logger.info("validation_attempt", attempt=attempt + 1)

            # Validate current code
            results = await validate_func(current_code, test_code)

            # Check if all passed
            if all(r.passed for r in results):
                logger.info("validation_passed", attempts=attempt + 1)
                return current_code, results, True

            # Collect errors for next iteration
            last_errors = []
            for result in results:
                if not result.passed:
                    last_errors.extend(result.errors)

            logger.warning(
                "validation_failed",
                attempt=attempt + 1,
                error_count=len(last_errors),
            )

            # If this was the last attempt, fail
            if attempt == max_attempts - 1:
                logger.error("correction_exhausted", attempts=max_attempts)
                return current_code, results, False

            # Attempt correction
            try:
                current_code = await self.correct_code(
                    original_code=current_code,
                    validation_results=results,
                    requirements=["Fix all validation errors"],
                )
            except Exception as e:
                logger.exception("correction_error", error=str(e))
                return current_code, results, False

        return current_code, [], False

    def format_error_context(
        self,
        validation_results: list[ValidationResult],
    ) -> str:
        """Format validation errors into a context string.

        Args:
            validation_results: List of validation results.

        Returns:
            Formatted error context string.
        """
        lines = ["## Validation Errors\n"]

        for result in validation_results:
            if not result.passed:
                lines.append(f"### {result.stage}")
                for error in result.errors:
                    lines.append(f"- {error}")
                lines.append("")

        return "\n".join(lines)
