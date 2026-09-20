"""Unit tests for CircuitBreaker (app/core/circuit_breaker.py).

The real implementation is per-provider and fully async: state is
addressed by provider name, not a bare CircuitBreaker attribute.
"""

import asyncio

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.core.exceptions import CircuitBreakerOpenError


class TestCircuitBreaker:
    """Test circuit breaker implementation."""

    def test_init(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30

    @pytest.mark.asyncio
    async def test_closed_state_allows_calls(self):
        cb = CircuitBreaker()
        assert await cb.get_state("groq") == CircuitState.CLOSED
        assert await cb.can_execute("groq") is True

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)

        await cb.record_failure("groq")
        await cb.record_failure("groq")
        assert await cb.get_state("groq") == CircuitState.CLOSED

        await cb.record_failure("groq")
        assert await cb.get_state("groq") == CircuitState.OPEN
        assert await cb.can_execute("groq") is False

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)

        await cb.record_failure("groq")
        assert await cb.get_state("groq") == CircuitState.OPEN

        await asyncio.sleep(1.1)

        assert await cb.get_state("groq") == CircuitState.HALF_OPEN
        assert await cb.can_execute("groq") is True

    @pytest.mark.asyncio
    async def test_closes_on_success_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)

        await cb.record_failure("groq")
        await asyncio.sleep(1.1)
        await cb.get_state("groq")  # transitions OPEN -> HALF_OPEN
        await cb.record_success("groq")

        assert await cb.get_state("groq") == CircuitState.CLOSED
        stats = await cb.get_stats("groq")
        assert stats["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)

        await cb.record_failure("groq")
        await asyncio.sleep(1.1)
        await cb.get_state("groq")  # transitions OPEN -> HALF_OPEN
        await cb.record_failure("groq")

        assert await cb.get_state("groq") == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_failure_count_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)

        await cb.record_failure("groq")
        await cb.record_failure("groq")
        stats = await cb.get_stats("groq")
        assert stats["failure_count"] == 2

        await cb.record_success("groq")
        stats = await cb.get_stats("groq")
        assert stats["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_check_and_raise_when_open(self):
        cb = CircuitBreaker(failure_threshold=1)

        await cb.record_failure("groq")

        with pytest.raises(CircuitBreakerOpenError):
            await cb.check_and_raise("groq")

    @pytest.mark.asyncio
    async def test_check_and_raise_allows_when_closed(self):
        cb = CircuitBreaker()
        await cb.check_and_raise("groq")  # must not raise

    @pytest.mark.asyncio
    async def test_providers_are_independent(self):
        cb = CircuitBreaker(failure_threshold=2)

        await cb.record_failure("groq")
        await cb.record_failure("groq")

        assert await cb.get_state("groq") == CircuitState.OPEN
        assert await cb.get_state("anthropic") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_multiple_instances_independent(self):
        cb1 = CircuitBreaker(failure_threshold=2)
        cb2 = CircuitBreaker(failure_threshold=2)

        await cb1.record_failure("groq")
        await cb1.record_failure("groq")

        assert await cb1.get_state("groq") == CircuitState.OPEN
        assert await cb2.get_state("groq") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_state_transitions(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        assert await cb.get_state("groq") == CircuitState.CLOSED

        await cb.record_failure("groq")
        await cb.record_failure("groq")
        assert await cb.get_state("groq") == CircuitState.OPEN

        await asyncio.sleep(1.1)
        assert await cb.get_state("groq") == CircuitState.HALF_OPEN

        await cb.record_success("groq")
        assert await cb.get_state("groq") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_get_stats(self):
        cb = CircuitBreaker()

        await cb.record_failure("groq")
        await cb.record_success("groq")
        await cb.record_failure("groq")

        stats = await cb.get_stats("groq")

        assert stats["state"] == "closed"
        assert stats["failure_count"] == 1  # reset by the success, then +1
        assert stats["total_failures"] >= 2

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        cb = CircuitBreaker(failure_threshold=1)

        await cb.record_failure("groq")
        assert await cb.get_state("groq") == CircuitState.OPEN

        await cb.reset("groq")
        assert await cb.get_state("groq") == CircuitState.CLOSED


if __name__ == "__main__":

    async def demo() -> None:
        cb = CircuitBreaker(failure_threshold=1)
        assert await cb.can_execute("demo") is True
        await cb.record_failure("demo")
        assert await cb.can_execute("demo") is False
        print("self-check passed")

    asyncio.run(demo())
