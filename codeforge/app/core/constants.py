"""Constants and enums for CodeForge."""

from enum import StrEnum, auto


class TaskStatus(StrEnum):
    """Task status enumeration."""

    PENDING = auto()
    INTENT_ANALYZING = auto()
    AWAITING_CONFIRMATION = auto()
    CONFIRMED = auto()
    DECOMPOSING = auto()
    GENERATING = auto()
    DEBATING = auto()
    SYNTHESIZING = auto()
    VALIDATING = auto()
    SANDBOX_EXECUTING = auto()
    CORRECTING = auto()
    COMPLETED = auto()
    FAILED = auto()


class ModelProvider(StrEnum):
    """LLM provider enumeration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    KIMI = "kimi"
    QWEN = "qwen"
    GEMINI = "gemini"


class TaskType(StrEnum):
    """Task type for routing decisions."""

    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    ALGORITHM = "algorithm"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    TESTING = "testing"


class ValidationStage(StrEnum):
    """Validation pipeline stages."""

    SYNTAX = "syntax"
    STATIC_ANALYSIS = "static_analysis"
    SECURITY_SCAN = "security_scan"
    UNIT_TESTS = "unit_tests"
    PROPERTY_TESTS = "property_tests"
    IMPORT_RESOLUTION = "import_resolution"


class ConfirmationStatus(StrEnum):
    """User confirmation status."""

    PENDING = auto()
    CONFIRMED = auto()
    REJECTED = auto()
    CLARIFIED = auto()


# Model routing defaults
DEFAULT_MODEL_TIMEOUT = 30
REASONING_MODEL_TIMEOUT = 120
MAX_CORRECTION_ATTEMPTS = 3
DEFAULT_ENSEMBLE_SIZE = 3

# Circuit breaker defaults
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 30

# Sandbox defaults
SANDBOX_TIMEOUT = 30
SANDBOX_MEMORY_LIMIT = "512m"
SANDBOX_CPU_LIMIT = 1.0

# Validation defaults
HYPOTHESIS_ITERATIONS = 100

# Task type to model mapping
TASK_TYPE_MODEL_MAP: dict[TaskType, ModelProvider] = {
    TaskType.ARCHITECTURE: ModelProvider.ANTHROPIC,
    TaskType.IMPLEMENTATION: ModelProvider.OPENAI,
    TaskType.ALGORITHM: ModelProvider.QWEN,
    TaskType.DOCUMENTATION: ModelProvider.KIMI,
    TaskType.ANALYSIS: ModelProvider.GEMINI,
    TaskType.DEBUGGING: ModelProvider.OPENAI,
    TaskType.TESTING: ModelProvider.ANTHROPIC,
}

# Model names per provider
PROVIDER_MODELS: dict[ModelProvider, list[str]] = {
    ModelProvider.OPENAI: ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    ModelProvider.ANTHROPIC: ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    ModelProvider.KIMI: ["kimi-k1.5"],
    ModelProvider.QWEN: ["qwen-2.5-coder-32b-instruct", "qwen-2.5-72b-instruct"],
    ModelProvider.GEMINI: ["gemini-1.5-pro", "gemini-1.5-flash"],
}
