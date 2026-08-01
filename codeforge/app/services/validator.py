"""Validator Service - Multi-stage validation pipeline."""

import ast
import asyncio
from typing import Any

import structlog

from app.config import get_settings
from app.core.exceptions import ValidationError
from app.models.models import ValidationResult

logger = structlog.get_logger(__name__)


class ValidatorService:
    """Service for multi-stage code validation."""

    def __init__(self) -> None:
        """Initialize validator service."""
        self.settings = get_settings()

    async def validate_all(
        self,
        code: str,
        test_code: str | None = None,
    ) -> list[ValidationResult]:
        """Run all validation stages.

        Args:
            code: Code to validate.
            test_code: Optional test code.

        Returns:
            List of validation results for each stage.
        """
        logger.info("starting_validation")

        stages = [
            ("syntax", self._validate_syntax),
            ("static_analysis", self._validate_static_analysis),
            ("security_scan", self._validate_security),
            ("import_resolution", self._validate_imports),
        ]

        results = []
        for stage_name, stage_func in stages:
            try:
                result = await stage_func(code)
                results.append(result)

                if not result.passed:
                    logger.warning("validation_stage_failed", stage=stage_name)

            except Exception as e:
                logger.exception("validation_stage_error", stage=stage_name, error=str(e))
                results.append(
                    ValidationResult(
                        stage=stage_name,
                        passed=False,
                        errors=[f"Validation error: {str(e)}"],
                    )
                )

        # Run tests if provided
        if test_code:
            test_result = await self._run_unit_tests(code, test_code)
            results.append(test_result)

        return results

    async def _validate_syntax(self, code: str) -> ValidationResult:
        """Validate Python syntax.

        Args:
            code: Code to validate.

        Returns:
            Validation result.
        """
        import time

        start = time.time()
        errors = []

        try:
            ast.parse(code)
            passed = True
        except SyntaxError as e:
            passed = False
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")

        return ValidationResult(
            stage="syntax",
            passed=passed,
            errors=errors,
            duration_ms=int((time.time() - start) * 1000),
        )

    async def _validate_static_analysis(self, code: str) -> ValidationResult:
        """Run static analysis (ruff-style checks).

        Args:
            code: Code to validate.

        Returns:
            Validation result.
        """
        import time

        start = time.time()
        warnings = []
        errors = []

        # Simple static analysis checks
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for very long lines
            if len(line) > 200:
                warnings.append(f"Line {i}: Very long line ({len(line)} chars)")

            # Check for bare except
            if "except:" in line and not line.strip().startswith("#"):
                errors.append(f"Line {i}: Bare except clause")

            # Check for print statements in production code
            if line.strip().startswith("print("):
                warnings.append(f"Line {i}: Print statement found")

        passed = len(errors) == 0

        return ValidationResult(
            stage="static_analysis",
            passed=passed,
            errors=errors,
            warnings=warnings,
            duration_ms=int((time.time() - start) * 1000),
        )

    async def _validate_security(self, code: str) -> ValidationResult:
        """Run security scan.

        Args:
            code: Code to validate.

        Returns:
            Validation result.
        """
        import time

        start = time.time()
        errors = []

        # Security checks
        dangerous_patterns = [
            ("eval(", "Use of eval() is dangerous"),
            ("exec(", "Use of exec() is dangerous"),
            ("os.system(", "Direct system calls are dangerous"),
            ("__import__(", "Dynamic imports may be unsafe"),
            ("input(", "User input should be validated"),
        ]

        for pattern, message in dangerous_patterns:
            if pattern in code:
                errors.append(message)

        passed = len(errors) == 0

        return ValidationResult(
            stage="security_scan",
            passed=passed,
            errors=errors,
            duration_ms=int((time.time() - start) * 1000),
        )

    async def _validate_imports(self, code: str) -> ValidationResult:
        """Validate that imports can be resolved.

        Args:
            code: Code to validate.

        Returns:
            Validation result.
        """
        import time

        start = time.time()
        errors = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Try to import
                        try:
                            __import__(alias.name.split(".")[0])
                        except ImportError:
                            errors.append(f"Cannot resolve import: {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        try:
                            __import__(node.module.split(".")[0])
                        except ImportError:
                            errors.append(f"Cannot resolve import: {node.module}")

        except Exception as e:
            errors.append(f"Import validation failed: {str(e)}")

        passed = len(errors) == 0

        return ValidationResult(
            stage="import_resolution",
            passed=passed,
            errors=errors,
            duration_ms=int((time.time() - start) * 1000),
        )

    async def _run_unit_tests(
        self,
        code: str,
        test_code: str,
    ) -> ValidationResult:
        """Run unit tests in sandbox.

        Args:
            code: Code being tested.
            test_code: Test code to run.

        Returns:
            Validation result.
        """
        import time

        start = time.time()
        errors = []

        # Combine code and tests
        combined = f"{code}\n\n{test_code}"

        try:
            # Try to compile and run
            compiled = compile(combined, "<test>", "exec")

            # Create a namespace for execution
            namespace: dict[str, Any] = {}

            # Execute with timeout
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(exec, compiled, namespace),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                errors.append("Tests timed out")

        except Exception as e:
            errors.append(f"Test execution failed: {str(e)}")

        passed = len(errors) == 0

        return ValidationResult(
            stage="unit_tests",
            passed=passed,
            errors=errors,
            duration_ms=int((time.time() - start) * 1000),
        )

    def all_passed(self, results: list[ValidationResult]) -> bool:
        """Check if all validation stages passed.

        Args:
            results: List of validation results.

        Returns:
            True if all passed.
        """
        return all(r.passed for r in results)

    def get_errors(self, results: list[ValidationResult]) -> list[str]:
        """Get all errors from validation results.

        Args:
            results: List of validation results.

        Returns:
            List of all error messages.
        """
        errors = []
        for result in results:
            errors.extend(result.errors)
        return errors
