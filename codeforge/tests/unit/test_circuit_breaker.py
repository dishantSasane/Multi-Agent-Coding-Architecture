"""Unit tests for circuit breaker."""

import time
import pytest

from app.core.circuit_breaker import CircuitBreaker
from app.core.exceptions import CircuitBreakerOpenError


class TestCircuitBreaker:
    """Test circuit breaker implementation."""

    def test_init(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30
        assert cb._failures == 0
        assert cb._last_failure_time is None

    def test_closed_state_allows_calls(self):
        """Test that closed state allows calls."""
        cb = CircuitBreaker()
        
        assert cb.is_closed() is True
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        """Test that circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record failures
        cb.record_failure()
        cb.record_failure()
        assert cb.is_closed() is True
        
        cb.record_failure()
        assert cb.is_open() is True
        assert cb.can_execute() is False

    def test_half_open_after_recovery_timeout(self):
        """Test that circuit becomes half-open after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        
        # Open the circuit
        cb.record_failure()
        assert cb.is_open() is True
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        assert cb.is_half_open() is True
        assert cb.can_execute() is True

    def test_closes_on_success_in_half_open(self):
        """Test that circuit closes on success in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        
        # Open the circuit
        cb.record_failure()
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Record success
        cb.record_success()
        
        assert cb.is_closed() is True
        assert cb._failures == 0

    def test_reopens_on_failure_in_half_open(self):
        """Test that circuit reopens on failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        
        # Open the circuit
        cb.record_failure()
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Record failure in half-open state
        cb.record_failure()
        
        assert cb.is_open() is True

    def test_failure_count_resets_on_success(self):
        """Test that failure count resets on success."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record some failures
        cb.record_failure()
        cb.record_failure()
        assert cb._failures == 2
        
        # Record success
        cb.record_success()
        assert cb._failures == 0

    def test_context_manager_success(self):
        """Test context manager with successful execution."""
        cb = CircuitBreaker()
        
        with cb.execute():
            pass  # Success
        
        assert cb.is_closed() is True

    def test_context_manager_failure(self):
        """Test context manager with failed execution."""
        cb = CircuitBreaker(failure_threshold=1)
        
        try:
            with cb.execute():
                raise Exception("Execution failed")
        except Exception:
            pass
        
        assert cb.is_open() is True

    def test_raises_circuit_breaker_open_error(self):
        """Test that open circuit raises CircuitBreakerOpenError."""
        cb = CircuitBreaker(failure_threshold=1)
        
        # Open the circuit
        cb.record_failure()
        
        with pytest.raises(CircuitBreakerOpenError):
            with cb.execute():
                pass

    def test_multiple_instances_independent(self):
        """Test that multiple circuit breaker instances are independent."""
        cb1 = CircuitBreaker(failure_threshold=2)
        cb2 = CircuitBreaker(failure_threshold=2)
        
        # Fail cb1
        cb1.record_failure()
        cb1.record_failure()
        
        assert cb1.is_open() is True
        assert cb2.is_closed() is True

    def test_state_transitions(self):
        """Test state machine transitions."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Initial state: CLOSED
        assert cb.state == "CLOSED"
        
        # Transition to OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        
        # Transition to HALF_OPEN
        time.sleep(1.1)
        assert cb.state == "HALF_OPEN"
        
        # Transition back to CLOSED
        cb.record_success()
        assert cb.state == "CLOSED"

    def test_get_stats(self):
        """Test statistics retrieval."""
        cb = CircuitBreaker()
        
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        
        stats = cb.get_stats()
        
        assert stats["state"] == "CLOSED"
        assert stats["failures"] == 0  # Reset on success
        assert stats["total_failures"] >= 2
