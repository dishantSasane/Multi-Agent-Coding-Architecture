"""Core module initialization."""

from app.core.circuit_breaker import CircuitBreaker, get_circuit_breaker
from app.core.constants import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    DEFAULT_ENSEMBLE_SIZE,
    DEFAULT_MODEL_TIMEOUT,
    HYPOTHESIS_ITERATIONS,
    MAX_CORRECTION_ATTEMPTS,
    PROVIDER_MODELS,
    REASONING_MODEL_TIMEOUT,
    SANDBOX_CPU_LIMIT,
    SANDBOX_MEMORY_LIMIT,
    SANDBOX_TIMEOUT,
    TASK_TYPE_MODEL_MAP,
    ConfirmationStatus,
    ModelProvider,
    TaskStatus,
    TaskType,
    ValidationStage,
)
from app.core.exceptions import (
    CircuitBreakerOpenError,
    CodeForgeException,
    ConfirmationRequiredError,
    IntentParsingError,
    ModelUnavailableError,
    SandboxExecutionError,
    SecurityViolationError,
    SelfCorrectionExhaustedError,
    TaskNotFoundError,
    ValidationError,
)
from app.core.security import InputSanitizer

__all__ = [
    # Constants
    "CIRCUIT_BREAKER_FAILURE_THRESHOLD",
    "CIRCUIT_BREAKER_RECOVERY_TIMEOUT",
    "DEFAULT_ENSEMBLE_SIZE",
    "DEFAULT_MODEL_TIMEOUT",
    "HYPOTHESIS_ITERATIONS",
    "MAX_CORRECTION_ATTEMPTS",
    "PROVIDER_MODELS",
    "REASONING_MODEL_TIMEOUT",
    "SANDBOX_CPU_LIMIT",
    "SANDBOX_MEMORY_LIMIT",
    "SANDBOX_TIMEOUT",
    "TASK_TYPE_MODEL_MAP",
    # Enums
    "ConfirmationStatus",
    "ModelProvider",
    "TaskStatus",
    "TaskType",
    "ValidationStage",
    # Exceptions
    "CircuitBreakerOpenError",
    "CodeForgeException",
    "ConfirmationRequiredError",
    "IntentParsingError",
    "ModelUnavailableError",
    "SandboxExecutionError",
    "SecurityViolationError",
    "SelfCorrectionExhaustedError",
    "TaskNotFoundError",
    "ValidationError",
    # Classes
    "CircuitBreaker",
    "InputSanitizer",
    # Functions
    "get_circuit_breaker",
]
