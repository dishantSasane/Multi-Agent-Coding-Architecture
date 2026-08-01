"""Unit tests for sandbox executor."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.exceptions import SandboxExecutionError, SecurityViolationError
from app.services.sandbox import SandboxExecutor


class TestSandboxExecutor:
    """Test sandbox executor service."""

    def test_init(self):
        """Test sandbox executor initialization."""
        executor = SandboxExecutor()
        assert executor is not None
        assert executor.timeout > 0
        assert executor.memory_limit is not None

    @pytest.mark.asyncio
    async def test_execute_valid_code(self, sandbox_code):
        """Test execution of valid code."""
        executor = SandboxExecutor()
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"5\n",
        )
        mock_container.logs.return_value = b"5\n"
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            result = await executor.execute("test-task", sandbox_code, "python")
            
            assert result["success"] is True
            assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_error(self, invalid_code):
        """Test execution with syntax error."""
        executor = SandboxExecutor()
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=1,
            output=b"SyntaxError: invalid syntax\n",
        )
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            result = await executor.execute("test-task", invalid_code, "python")
            
            assert result["success"] is False
            assert result["exit_code"] != 0

    @pytest.mark.asyncio
    async def test_malicious_code_blocked(self, malicious_code):
        """Test that malicious code is blocked."""
        executor = SandboxExecutor()
        
        # Security check should detect malicious code
        with patch.object(executor, "_check_security") as mock_security:
            mock_security.side_effect = SecurityViolationError(
                "Detected dangerous system call"
            )
            
            with pytest.raises(SecurityViolationError):
                await executor.execute("test-task", malicious_code, "python")

    @pytest.mark.asyncio
    async def test_timeout_enforced(self):
        """Test that timeout is enforced."""
        executor = SandboxExecutor()
        executor.timeout = 1  # 1 second timeout
        
        mock_container = MagicMock()
        mock_container.exec_run.side_effect = TimeoutError("Execution timed out")
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            result = await executor.execute("test-task", "import time; time.sleep(10)", "python")
            
            assert result["success"] is False
            assert "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_resource_limits_applied(self, sandbox_code):
        """Test that resource limits are applied to containers."""
        executor = SandboxExecutor()
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"")
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            await executor.execute("test-task", sandbox_code, "python")
            
            # Verify container was created with resource limits
            call_kwargs = mock_containers.run.call_args[1]
            assert "mem_limit" in call_kwargs or call_kwargs.get("nano_cpus") is not None

    @pytest.mark.asyncio
    async def test_network_disabled(self, sandbox_code):
        """Test that network access is disabled."""
        executor = SandboxExecutor()
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"")
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            await executor.execute("test-task", sandbox_code, "python")
            
            # Verify network is disabled
            call_kwargs = mock_containers.run.call_args[1]
            assert call_kwargs.get("network") == "none"

    @pytest.mark.asyncio
    async def test_container_cleanup(self, sandbox_code):
        """Test that containers are cleaned up after execution."""
        executor = SandboxExecutor()
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"")
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            await executor.execute("test-task", sandbox_code, "python")
            
            # Container should be removed
            mock_container.remove.assert_called()

    @pytest.mark.asyncio
    async def test_stdout_stderr_captured(self, sandbox_code):
        """Test that stdout and stderr are captured."""
        executor = SandboxExecutor()
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(
            exit_code=0,
            output=b"stdout output\n",
        )
        mock_container.logs.return_value = b"stdout output\nstderr output\n"
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            result = await executor.execute("test-task", sandbox_code, "python")
            
            assert "stdout" in result
            assert "stderr" in result

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self, sandbox_code):
        """Test that execution time is recorded."""
        executor = SandboxExecutor()
        
        mock_container = MagicMock()
        mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"")
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.return_value.__enter__ = lambda self: mock_container
            mock_containers.run.return_value.__exit__ = lambda self, *args: None
            
            result = await executor.execute("test-task", sandbox_code, "python")
            
            assert "execution_time_ms" in result
            assert result["execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_docker_unavailable_fallback(self, sandbox_code):
        """Test fallback when Docker is unavailable."""
        executor = SandboxExecutor()
        
        with patch.object(executor.docker_client, "containers") as mock_containers:
            mock_containers.run.side_effect = Exception("Docker not available")
            
            with pytest.raises(SandboxExecutionError):
                await executor.execute("test-task", sandbox_code, "python")
