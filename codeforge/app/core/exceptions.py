"""Custom exception hierarchy for CodeForge."""


class CodeForgeException(Exception):
    """Base exception for all CodeForge errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class IntentParsingError(CodeForgeException):
    """Raised when intent parsing fails."""

    pass


class ModelUnavailableError(CodeForgeException):
    """Raised when a requested LLM model is unavailable."""

    def __init__(self, provider: str, model: str, details: dict | None = None) -> None:
        super().__init__(
            message=f"Model {model} from provider {provider} is unavailable",
            details={"provider": provider, "model": model, **(details or {})},
        )


class SandboxExecutionError(CodeForgeException):
    """Raised when sandbox execution fails."""

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        timeout: bool = False,
    ) -> None:
        super().__init__(
            message=message,
            details={
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "timeout": timeout,
            },
        )


class ValidationError(CodeForgeException):
    """Raised when validation fails."""

    def __init__(self, stage: str, message: str, errors: list[str] | None = None) -> None:
        super().__init__(
            message=message,
            details={"stage": stage, "errors": errors or []},
        )


class SelfCorrectionExhaustedError(CodeForgeException):
    """Raised when self-correction retries are exhausted."""

    def __init__(self, attempts: int, last_error: str) -> None:
        super().__init__(
            message=f"Self-correction exhausted after {attempts} attempts",
            details={"attempts": attempts, "last_error": last_error},
        )


class SecurityViolationError(CodeForgeException):
    """Raised when a security violation is detected."""

    def __init__(self, violation_type: str, details: dict | None = None) -> None:
        super().__init__(
            message=f"Security violation detected: {violation_type}",
            details={"violation_type": violation_type, **(details or {})},
        )


class CircuitBreakerOpenError(CodeForgeException):
    """Raised when circuit breaker is open for a provider."""

    def __init__(self, provider: str, recovery_seconds: int) -> None:
        super().__init__(
            message=f"Circuit breaker open for provider {provider}",
            details={"provider": provider, "recovery_seconds": recovery_seconds},
        )


class TaskNotFoundError(CodeForgeException):
    """Raised when a task is not found."""

    def __init__(self, task_id: str) -> None:
        super().__init__(
            message=f"Task {task_id} not found",
            details={"task_id": task_id},
        )


class ConfirmationRequiredError(CodeForgeException):
    """Raised when user confirmation is required before proceeding."""

    def __init__(self, questions: list[str]) -> None:
        super().__init__(
            message="User confirmation required before proceeding",
            details={"questions": questions},
        )
