"""Unit tests for ValidatorService (app/services/validator.py)."""

import pytest

from app.services.validator import ValidatorService


class TestValidatorService:
    """Test validator service."""

    def test_init(self):
        validator = ValidatorService()
        assert validator is not None

    @pytest.mark.asyncio
    async def test_validate_syntax_valid_code(self, sandbox_code):
        validator = ValidatorService()
        result = await validator._validate_syntax(sandbox_code)

        assert result.passed is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_validate_syntax_invalid_code(self, invalid_code):
        validator = ValidatorService()
        result = await validator._validate_syntax(invalid_code)

        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_static_analysis_flags_bare_except(self):
        validator = ValidatorService()
        code = "try:\n    pass\nexcept:\n    pass\n"

        result = await validator._validate_static_analysis(code)

        assert result.passed is False
        assert any("Bare except" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_static_analysis_warns_on_print(self):
        validator = ValidatorService()
        result = await validator._validate_static_analysis("print('hi')\n")

        assert result.passed is True
        assert any("Print statement" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_security_flags_eval(self):
        validator = ValidatorService()
        result = await validator._validate_security("eval('1+1')")

        assert result.passed is False
        assert any("eval" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_security_flags_exec(self, malicious_code):
        validator = ValidatorService()
        result = await validator._validate_security(malicious_code)

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_validate_security_passes_clean_code(self, sandbox_code):
        validator = ValidatorService()
        result = await validator._validate_security(sandbox_code)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_validate_imports_resolves_stdlib(self):
        validator = ValidatorService()
        result = await validator._validate_imports("import json\nimport os\n")

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_validate_imports_skips_local_modules(self):
        validator = ValidatorService()
        # "database" and "models" look like local project files, not
        # installed packages — should not be flagged as unresolved.
        result = await validator._validate_imports("import database\nfrom models import User\n")

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_validate_imports_skips_multi_file_blocks(self):
        validator = ValidatorService()
        code = "# models.py\nimport nonexistent_totally_fake_package\n"

        result = await validator._validate_imports(code)

        assert result.passed is True
        assert any("multi-file" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_all_single_file(self, sandbox_code):
        validator = ValidatorService()
        results = await validator.validate_all(sandbox_code)

        stages = {r.stage for r in results}
        assert {"syntax", "static_analysis", "security_scan", "import_resolution"} <= stages
        assert validator.all_passed(results) is True

    @pytest.mark.asyncio
    async def test_validate_all_empty_code_fails(self):
        validator = ValidatorService()
        results = await validator.validate_all("   ")

        assert len(results) == 1
        assert results[0].stage == "generation"
        assert results[0].passed is False

    @pytest.mark.asyncio
    async def test_validate_all_multi_file(self):
        validator = ValidatorService()
        files = [
            {"filename": "main.py", "content": "import helpers\nprint(helpers.f())"},
            {"filename": "helpers.py", "content": "def f():\n    return 1\n"},
        ]

        results = await validator.validate_all("", files=files)

        assert validator.all_passed(results) is True

    def test_all_passed_true_when_no_failures(self):
        validator = ValidatorService()
        from app.models.models import ValidationResult

        results = [ValidationResult(stage="syntax", passed=True)]
        assert validator.all_passed(results) is True

    def test_all_passed_false_when_any_failure(self):
        validator = ValidatorService()
        from app.models.models import ValidationResult

        results = [
            ValidationResult(stage="syntax", passed=True),
            ValidationResult(stage="security_scan", passed=False, errors=["eval used"]),
        ]
        assert validator.all_passed(results) is False

    def test_get_errors_collects_from_all_stages(self):
        validator = ValidatorService()
        from app.models.models import ValidationResult

        results = [
            ValidationResult(stage="syntax", passed=False, errors=["bad syntax"]),
            ValidationResult(stage="security_scan", passed=False, errors=["eval used"]),
        ]
        errors = validator.get_errors(results)
        assert errors == ["bad syntax", "eval used"]

    def test_redact_preview_hides_secrets(self):
        preview = ValidatorService._redact_preview("api_key: sk-abc123, other=1")
        assert "sk-abc123" not in preview
        assert "[REDACTED]" in preview


if __name__ == "__main__":
    import asyncio

    async def demo() -> None:
        validator = ValidatorService()
        result = await validator._validate_syntax("x = 1")
        assert result.passed is True
        print("self-check passed")

    asyncio.run(demo())
