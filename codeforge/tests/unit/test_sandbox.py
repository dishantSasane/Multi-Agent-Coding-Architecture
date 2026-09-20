"""Unit tests for SandboxService (app/services/sandbox.py)."""

from unittest.mock import MagicMock

import pytest
from docker.errors import APIError

from app.core.exceptions import SandboxExecutionError
from app.services.sandbox import SandboxService


class TestSandboxService:
    """Test sandbox service."""

    def test_init(self):
        service = SandboxService()
        assert service is not None
        assert service.settings.sandbox_timeout > 0
        assert service.settings.sandbox_memory_limit

    @pytest.mark.asyncio
    async def test_execute_python_skips_when_sandbox_disabled(self):
        service = SandboxService()
        service.settings.sandbox_enabled = False
        service.client = None

        result = await service.execute_python("print(1)")

        assert result["success"] is True
        assert result["skipped"] is True

    @pytest.mark.asyncio
    async def test_execute_python_success(self, sandbox_code):
        service = SandboxService()
        service.settings.sandbox_enabled = True
        service.client = MagicMock()
        service.client.containers.run.return_value = b"5\n"

        result = await service.execute_python(sandbox_code)

        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "5" in result["stdout"]

    @pytest.mark.asyncio
    async def test_execute_python_resource_limits_applied(self, sandbox_code):
        service = SandboxService()
        service.settings.sandbox_enabled = True
        service.client = MagicMock()
        service.client.containers.run.return_value = b""

        await service.execute_python(sandbox_code)

        call_kwargs = service.client.containers.run.call_args[1]
        assert call_kwargs["mem_limit"] == service.settings.sandbox_memory_limit
        assert call_kwargs["network_disabled"] is True
        assert call_kwargs["read_only"] is True
        assert call_kwargs["cap_drop"] == ["ALL"]

    @pytest.mark.asyncio
    async def test_execute_python_docker_api_error_raises_sandbox_error(self, sandbox_code):
        service = SandboxService()
        service.settings.sandbox_enabled = True
        service.client = MagicMock()
        service.client.containers.run.side_effect = APIError("docker daemon unavailable")

        with pytest.raises(SandboxExecutionError):
            await service.execute_python(sandbox_code)

    @pytest.mark.asyncio
    async def test_execute_python_with_multi_file_project(self):
        service = SandboxService()
        service.settings.sandbox_enabled = True
        service.client = MagicMock()
        service.client.containers.run.return_value = b"ok\n"

        files = [
            {"filename": "main.py", "content": "import helpers\nprint('ok')"},
            {"filename": "helpers.py", "content": "def f(): return 1"},
        ]

        result = await service.execute_python("", files=files)

        assert result["success"] is True
        call_kwargs = service.client.containers.run.call_args[1]
        assert "main.py" in call_kwargs["command"]

    @pytest.mark.asyncio
    async def test_validate_syntax_valid_code(self):
        service = SandboxService()
        valid, error = await service.validate_syntax("x = 1 + 1")
        assert valid is True
        assert error == ""

    @pytest.mark.asyncio
    async def test_validate_syntax_invalid_code(self, invalid_code):
        service = SandboxService()
        valid, error = await service.validate_syntax(invalid_code)
        assert valid is False
        assert "Syntax error" in error

    @pytest.mark.asyncio
    async def test_check_imports_flags_dangerous_modules(self, malicious_code):
        service = SandboxService()
        found = await service.check_imports(malicious_code)
        assert len(found) > 0

    @pytest.mark.asyncio
    async def test_check_imports_clean_code(self, sandbox_code):
        service = SandboxService()
        found = await service.check_imports(sandbox_code)
        assert found == []


if __name__ == "__main__":
    import asyncio

    async def demo() -> None:
        service = SandboxService()
        service.settings.sandbox_enabled = False
        service.client = None
        result = await service.execute_python("print(1)")
        assert result["skipped"] is True
        print("self-check passed")

    asyncio.run(demo())
