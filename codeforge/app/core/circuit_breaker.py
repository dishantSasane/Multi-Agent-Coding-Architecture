"""Circuit breaker implementation for LLM API calls."""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from app.config import get_settings
from app.core.exceptions import CircuitBreakerOpenError

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit."""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    total_requests: int = 0
    total_failures: int = 0


class CircuitBreaker:
    """Circuit breaker for LLM API providers.

    Implements the circuit breaker pattern to prevent cascading failures
    when an LLM provider is experiencing issues.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Seconds to wait before attempting recovery.
        """
        settings = get_settings()
        self.failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
        self.recovery_timeout = recovery_timeout or settings.circuit_breaker_recovery_timeout

        # State per provider
        self._states: dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self._stats: dict[str, CircuitStats] = defaultdict(CircuitStats)
        self._lock = asyncio.Lock()

    async def get_state(self, provider: str) -> CircuitState:
        """Get current state for a provider.

        Args:
            provider: Provider name.

        Returns:
            Current circuit state.
        """
        async with self._lock:
            state = self._states[provider]

            # Check if we should transition from OPEN to HALF_OPEN
            if state == CircuitState.OPEN:
                stats = self._stats[provider]
                if stats.last_failure_time:
                    elapsed = time.time() - stats.last_failure_time
                    if elapsed >= self.recovery_timeout:
                        logger.info("circuit_breaker_transition", provider=provider, from_state="OPEN", to_state="HALF_OPEN")
                        self._states[provider] = CircuitState.HALF_OPEN
                        return CircuitState.HALF_OPEN

            return state

    async def record_success(self, provider: str) -> None:
        """Record a successful call.

        Args:
            provider: Provider name.
        """
        async with self._lock:
            stats = self._stats[provider]
            stats.success_count += 1
            stats.total_requests += 1
            stats.last_success_time = time.time()
            stats.failure_count = 0  # Reset failure count on success

            # Transition from HALF_OPEN to CLOSED
            if self._states[provider] == CircuitState.HALF_OPEN:
                logger.info("circuit_breaker_transition", provider=provider, from_state="HALF_OPEN", to_state="CLOSED")
                self._states[provider] = CircuitState.CLOSED

            logger.debug("circuit_breaker_success", provider=provider, stats=vars(stats))

    async def record_failure(self, provider: str, error: str | None = None) -> None:
        """Record a failed call.

        Args:
            provider: Provider name.
            error: Optional error message.
        """
        async with self._lock:
            stats = self._stats[provider]
            stats.failure_count += 1
            stats.total_failures += 1
            stats.total_requests += 1
            stats.last_failure_time = time.time()

            logger.warning(
                "circuit_breaker_failure",
                provider=provider,
                failure_count=stats.failure_count,
                threshold=self.failure_threshold,
                error=error,
            )

            # Transition from CLOSED to OPEN
            if self._states[provider] == CircuitState.CLOSED and stats.failure_count >= self.failure_threshold:
                logger.warning(
                    "circuit_breaker_opened",
                    provider=provider,
                    failure_count=stats.failure_count,
                )
                self._states[provider] = CircuitState.OPEN

            # Transition from HALF_OPEN to OPEN
            elif self._states[provider] == CircuitState.HALF_OPEN:
                logger.warning(
                    "circuit_breaker_reopened",
                    provider=provider,
                    reason="failure_in_half_open_state",
                )
                self._states[provider] = CircuitState.OPEN

    async def can_execute(self, provider: str) -> bool:
        """Check if execution is allowed for a provider.

        Args:
            provider: Provider name.

        Returns:
            True if execution is allowed, False otherwise.
        """
        state = await self.get_state(provider)
        return state != CircuitState.OPEN

    async def check_and_raise(self, provider: str) -> None:
        """Check if execution is allowed, raise if not.

        Args:
            provider: Provider name.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
        """
        state = await self.get_state(provider)
        if state == CircuitState.OPEN:
            stats = self._stats[provider]
            raise CircuitBreakerOpenError(provider=provider, recovery_seconds=self.recovery_timeout)

    async def get_stats(self, provider: str) -> dict[str, Any]:
        """Get statistics for a provider.

        Args:
            provider: Provider name.

        Returns:
            Dictionary of statistics.
        """
        async with self._lock:
            stats = self._stats[provider]
            return {
                "provider": provider,
                "state": self._states[provider].value,
                "failure_count": stats.failure_count,
                "success_count": stats.success_count,
                "total_requests": stats.total_requests,
                "total_failures": stats.total_failures,
                "failure_rate": stats.total_failures / max(1, stats.total_requests),
            }

    async def reset(self, provider: str | None = None) -> None:
        """Reset circuit breaker state.

        Args:
            provider: Provider to reset, or None for all providers.
        """
        async with self._lock:
            if provider:
                self._states[provider] = CircuitState.CLOSED
                self._stats[provider] = CircuitStats()
                logger.info("circuit_breaker_reset", provider=provider)
            else:
                self._states.clear()
                self._stats.clear()
                logger.info("circuit_breaker_reset_all")


# Global circuit breaker instance
_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
