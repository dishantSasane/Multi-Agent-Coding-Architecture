"""Sandbox Service - Secure Docker-based code execution."""

import asyncio
import io
import tarfile
import tempfile
from typing import Any

import docker
import structlog
from docker.errors import APIError, ContainerError, ImageNotFound

from app.config import get_settings
from app.core.exceptions import SandboxExecutionError

logger = structlog.get_logger(__name__)


class SandboxService:
    """Service for executing code in secure Docker containers."""

    def __init__(self) -> None:
        """Initialize sandbox service."""
        self.settings = get_settings()
        self.client = docker.from_env()
        self._cleanup_lock = asyncio.Lock()

    async def execute_python(
        self,
        code: str,
        test_code: str | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute Python code in a sandboxed container.

        Args:
            code: Python code to execute.
            test_code: Optional test code to run after main code.
            timeout: Execution timeout in seconds.

        Returns:
            Execution results dictionary.

        Raises:
            SandboxExecutionError: If execution fails.
        """
        timeout = timeout or self.settings.sandbox_timeout

        logger.info("executing_in_sandbox", timeout=timeout)

        try:
            # Create combined script
            script = code
            if test_code:
                script += "\n\n" + test_code

            # Run container
            result = await asyncio.to_thread(
                self._run_container,
                script,
                timeout,
            )

            logger.info(
                "sandbox_execution_complete",
                exit_code=result["exit_code"],
                execution_time_ms=result.get("execution_time_ms"),
            )

            return result

        except SandboxExecutionError:
            raise
        except Exception as e:
            logger.exception("sandbox_error", error=str(e))
            raise SandboxExecutionError(
                message=f"Sandbox execution failed: {str(e)}",
                stderr=str(e),
            )

    def _run_container(
        self,
        script: str,
        timeout: int,
    ) -> dict[str, Any]:
        """Run code in a Docker container (synchronous).

        Args:
            script: Python script to execute.
            timeout: Timeout in seconds.

        Returns:
            Execution results.
        """
        container = None
        start_time = asyncio.get_event_loop().time()

        try:
            # Create temporary file with script
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(script)
                script_path = f.name

            # Run container
            container = self.client.containers.run(
                image="python:3.11-slim",
                command=f"python /app/script.py",
                volumes={script_path: {"bind": "/app/script.py", "mode": "ro"}},
                mem_limit=self.settings.sandbox_memory_limit,
                nano_cpus=int(self.settings.sandbox_cpu_limit * 1e9),
                network_disabled=True,  # No network access
                read_only=True,  # Read-only filesystem
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],  # Drop all capabilities
                remove=True,  # Auto-remove after execution
                detach=False,
            )

            # Get output
            result = {
                "success": True,
                "exit_code": 0,
                "stdout": container.decode("utf-8") if isinstance(container, bytes) else str(container),
                "stderr": "",
                "execution_time_ms": int((asyncio.get_event_loop().time() - start_time) * 1000),
                "timeout": False,
            }

            return result

        except ContainerError as e:
            return {
                "success": False,
                "exit_code": e.exit_status,
                "stdout": "",
                "stderr": e.stderr.decode("utf-8") if e.stderr else str(e),
                "execution_time_ms": int((asyncio.get_event_loop().time() - start_time) * 1000),
                "timeout": False,
                "error_message": str(e),
            }
        except APIError as e:
            raise SandboxExecutionError(
                message="Docker API error",
                stderr=str(e),
            )
        except ImageNotFound:
            # Pull image if not found
            logger.info("pulling_image", image="python:3.11-slim")
            self.client.images.pull("python:3.11-slim")
            return self._run_container(script, timeout)
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    async def validate_syntax(self, code: str) -> tuple[bool, str]:
        """Validate Python syntax without executing.

        Args:
            code: Python code to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            compile(code, "<string>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"

    async def check_imports(self, code: str) -> list[str]:
        """Check for potentially dangerous imports.

        Args:
            code: Python code to check.

        Returns:
            List of dangerous imports found.
        """
        dangerous_imports = [
            "os.system",
            "os.popen",
            "subprocess",
            "socket",
            "urllib.request",
            "http.client",
            "ftplib",
            "smtplib",
            "telnetlib",
            "pickle",
            "marshal",
            "shelve",
        ]

        found = []
        for imp in dangerous_imports:
            if imp in code:
                found.append(imp)

        return found
