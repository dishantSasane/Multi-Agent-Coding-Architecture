"""Validator Service - Multi-stage validation pipeline."""

import ast
import asyncio
import re
import sys
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Known-good module set — imports whose top-level name is in this set will
# be validated; single-word names NOT in this set are assumed to be local
# project files and are silently skipped.
#
# Contains: Python stdlib (sys.stdlib_module_names on 3.10+, else a curated
# fallback) PLUS common installed packages that are almost always present in
# the generated code's runtime environment.
# ---------------------------------------------------------------------------
_KNOWN_MODULES: frozenset[str] = (
    getattr(sys, "stdlib_module_names", None)
    or (
        frozenset(sys.builtin_module_names)
        | {
            "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect",
            "codecs", "collections", "concurrent", "configparser", "contextlib",
            "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal",
            "difflib", "dis", "email", "enum", "fractions", "functools", "glob",
            "gzip", "hashlib", "heapq", "hmac", "html", "http", "importlib",
            "inspect", "io", "itertools", "json", "locale", "logging", "math",
            "multiprocessing", "numbers", "operator", "os", "pathlib", "pickle",
            "platform", "pprint", "queue", "random", "re", "reprlib", "select",
            "shelve", "shutil", "signal", "socket", "sqlite3", "statistics",
            "string", "struct", "subprocess", "sys", "tarfile", "tempfile",
            "textwrap", "threading", "time", "traceback", "typing", "unicodedata",
            "unittest", "urllib", "uuid", "warnings", "weakref", "xml", "zipfile",
            "zlib", "gettext",
        }
    )
    # Well-known installed packages that appear frequently in generated code.
    | {
        "fastapi", "sqlalchemy", "pydantic", "celery", "redis", "httpx",
        "aiohttp", "starlette", "uvicorn", "alembic", "flask", "django",
        "requests", "aiofiles", "structlog", "pytest", "anyio", "click",
        "cryptography", "jose", "passlib", "bcrypt", "boto3", "botocore",
        "yaml", "toml", "dotenv", "PIL", "numpy", "pandas", "scipy",
    }
)

from app.config import get_settings
from app.models.models import ValidationResult
from app.services.code_extractor import file_metadata, normalize_filename

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
        files: list[dict[str, str]] | None = None,
    ) -> list[ValidationResult]:
        """Run all validation stages.

        Args:
            code: Code to validate.
            test_code: Optional test code.
            files: Optional extracted multi-file representation.

        Returns:
            List of validation results for each stage.
        """
        file_map = self._normalize_files(code, files)
        if not file_map or not any(content.strip() for content in file_map.values()):
            return [
                ValidationResult(
                    stage="generation",
                    passed=False,
                    errors=["Generated project is empty"],
                )
            ]
        structured_files = files is not None or len(file_map) > 1
        logger.info(
            "starting_validation",
            file_count=len(file_map),
            file_paths=list(file_map),
            code_preview=repr(self._redact_preview(code[:2000])),
        )

        stages = [
            ("syntax", self._validate_syntax),
            ("static_analysis", self._validate_static_analysis),
            ("security_scan", self._validate_security),
            ("import_resolution", self._validate_imports),
        ]

        results = []
        for stage_name, stage_func in stages:
            try:
                if structured_files:
                    result = await self._validate_files(stage_name, stage_func, file_map)
                else:
                    result = await stage_func(code)
                results.append(result)

                if not result.passed:
                    logger.warning(
                        "validation_stage_failed",
                        stage=stage_name,
                        errors=result.errors,
                        warnings=result.warnings,
                    )

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

    async def _validate_files(
        self,
        stage_name: str,
        stage_func: Any,
        files: dict[str, str],
    ) -> ValidationResult:
        """Run a validation stage independently for every generated file."""
        errors: list[str] = []
        warnings: list[str] = []
        duration_ms = 0

        for filename, content in files.items():
            language, _ = file_metadata(filename)
            if language != "python":
                continue
            result = await stage_func(content)
            duration_ms += result.duration_ms or 0
            errors.extend(f"{filename}: {error}" for error in result.errors)
            warnings.extend(f"{filename}: {warning}" for warning in result.warnings)

        return ValidationResult(
            stage=stage_name,
            passed=not errors,
            errors=errors,
            warnings=warnings,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _normalize_files(
        code: str,
        files: list[dict[str, str]] | None,
    ) -> dict[str, str]:
        """Return generated Python files, with legacy marker parsing fallback."""
        if files:
            return {
                normalize_filename(item["filename"]): item["content"]
                for item in files
                if item.get("filename") and isinstance(item.get("content"), str)
            }

        pattern = r"^#\s*={10,}\s+([^\s=]+)\s*={10,}\s*$"
        matches = list(re.finditer(pattern, code, re.MULTILINE))
        if len(matches) < 2:
            return {"<generated>.py": code}

        parsed: dict[str, str] = {}
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(code)
            parsed[match.group(1)] = code[match.end():end].strip()
        return parsed or {"<generated>.py": code}

    @staticmethod
    def _redact_preview(preview: str) -> str:
        """Redact credential-like values before writing generated text to logs."""
        secret_key = re.compile(
            r"(?i)(api[_-]?key|token|password|secret|credential|oauth|access[_-]?key)"
            r"(\s*[:=]\s*)([^\s,}]+)"
        )
        return secret_key.sub(r"\1\2[REDACTED]", preview)

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

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                function_name = self._called_name(node.func)
                if function_name == "eval":
                    errors.append("Use of eval() is dangerous")
                elif function_name == "exec":
                    errors.append("Use of exec() is dangerous")
                elif function_name == "os.system":
                    errors.append("Direct system calls are dangerous")
                elif function_name == "__import__":
                    errors.append("Dynamic imports may be unsafe")
        except SyntaxError:
            # Syntax validation reports malformed code; avoid substring-based
            # security false positives when the source cannot be parsed.
            pass

        passed = len(errors) == 0

        return ValidationResult(
            stage="security_scan",
            passed=passed,
            errors=errors,
            duration_ms=int((time.time() - start) * 1000),
        )

    @staticmethod
    def _called_name(node: ast.AST) -> str:
        """Return a dotted function name for a simple call expression."""
        names: list[str] = []
        while isinstance(node, ast.Attribute):
            names.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            names.append(node.id)
        return ".".join(reversed(names))

    @staticmethod
    def _should_validate_module(module_name: str) -> bool:
        """Return True if *module_name* should be import-validated.

        Rules:
        - Multi-part names (contain a dot) → always validate, e.g. ``sqlalchemy.orm``.
        - Single-word names in the known-modules set → validate (stdlib / common pkg).
        - Single-word names NOT in the set → skip; they are local project files
          such as ``database``, ``models``, ``routes``, ``config``.
        """
        if not module_name:
            return False
        if "." in module_name:
            return True
        return module_name in _KNOWN_MODULES

    @staticmethod
    def _is_multi_file_block(code: str) -> bool:
        """Return True when *code* looks like a multi-file code block.

        Multi-file blocks (e.g. LLM output that concatenates several files
        separated by comments) cannot be validated as a single module.
        Heuristics used:
          - A ``# <name>.py`` filename comment appears at least once
          - A ``# ---`` / ``# ===`` section-separator comment appears
          - ``if __name__ == "__main__":`` appears more than once
        Any single match is enough to skip import-resolution.
        """
        import re

        # e.g.  "# models.py"  or  "# utils/helpers.py"
        if re.search(r"#\s+\w[\w/]*\.py\b", code):
            return True
        # e.g.  "# ---" / "# ===" / "# ----"
        if re.search(r"#\s*[-=]{3,}", code):
            return True
        # Multiple entry-point guards  → concatenated scripts
        if code.count('if __name__') > 1:
            return True
        return False

    async def _validate_imports(self, code: str) -> ValidationResult:
        """Validate that imports can be resolved.

        Skipped automatically for multi-file code blocks — import paths that
        span multiple files will always fail single-module resolution.

        Args:
            code: Code to validate.

        Returns:
            Validation result.
        """
        import time

        start = time.time()
        errors = []

        # Multi-file blocks cannot be validated as a single module.
        if self._is_multi_file_block(code):
            return ValidationResult(
                stage="import_resolution",
                passed=True,
                warnings=["Skipped: multi-file code block detected"],
                duration_ms=int((time.time() - start) * 1000),
            )

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._should_validate_module(alias.name):
                            continue
                        try:
                            __import__(alias.name.split(".")[0])
                        except ImportError:
                            errors.append(f"Cannot resolve import: {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if not self._should_validate_module(node.module):
                            continue
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
