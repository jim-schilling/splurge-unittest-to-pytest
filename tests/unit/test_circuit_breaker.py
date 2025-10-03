"""Tests for circuit breaker functionality."""

import time
from unittest.mock import Mock, patch

import pytest

from splurge_unittest_to_pytest.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenException,
    CircuitBreakerStats,
    CircuitState,
    get_circuit_breaker,
    get_circuit_breaker_stats,
    reset_circuit_breaker,
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 2
        assert config.timeout is None
        assert config.max_retries == 0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=120.0,
            success_threshold=3,
            timeout=30.0,
            max_retries=2,
        )
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 120.0
        assert config.success_threshold == 3
        assert config.timeout == 30.0
        assert config.max_retries == 2


class TestCircuitBreakerStats:
    """Test CircuitBreakerStats dataclass."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = CircuitBreakerStats()
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.consecutive_failures == 0
        assert stats.last_failure_time is None
        assert stats.last_success_time is None

    def test_stats_updates(self):
        """Test statistics update operations."""
        stats = CircuitBreakerStats()

        # Test successful call stats
        stats.total_calls = 1
        stats.successful_calls = 1
        assert stats.total_calls == 1
        assert stats.successful_calls == 1
        assert stats.failed_calls == 0

        # Test failed call stats
        stats.total_calls = 2
        stats.failed_calls = 1
        stats.consecutive_failures = 1
        assert stats.total_calls == 2
        assert stats.successful_calls == 1
        assert stats.failed_calls == 1
        assert stats.consecutive_failures == 1


class TestCircuitBreakerOpenException:
    """Test CircuitBreakerOpenException."""

    def test_exception_creation(self):
        """Test exception creation with stats."""
        stats = CircuitBreakerStats(total_calls=10, successful_calls=5, failed_calls=5)
        exception = CircuitBreakerOpenException("test_circuit", stats)

        assert "test_circuit" in str(exception)
        assert "Circuit breaker 'test_circuit' is open" in str(exception)

    def test_exception_creation_with_message(self):
        """Test exception creation generates appropriate message."""
        stats = CircuitBreakerStats(total_calls=5, failed_calls=3, consecutive_failures=2)
        exception = CircuitBreakerOpenException("test_circuit", stats)

        assert "Circuit breaker 'test_circuit' is open" in str(exception)
        assert "5 calls" in str(exception)
        assert "3 failures" in str(exception)
        assert "2 consecutive" in str(exception)


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_initial_state(self):
        """Test circuit breaker initial state."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker("test_circuit", config)

        assert cb.name == "test_circuit"
        assert cb.state == CircuitState.CLOSED
        assert cb.config == config
        assert cb.stats.total_calls == 0

    def test_successful_call(self):
        """Test successful call handling."""
        cb = CircuitBreaker("test", CircuitBreakerConfig())

        def successful_func():
            return "success"

        result = cb.call(successful_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.total_calls == 1
        assert cb.stats.successful_calls == 1

    def test_failed_call_under_threshold(self):
        """Test failed call under failure threshold."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))

        def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            cb.call(failing_func)

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.total_calls == 1
        assert cb.stats.failed_calls == 1
        assert cb.stats.consecutive_failures == 1

    def test_failed_call_over_threshold_opens_circuit(self):
        """Test that exceeding failure threshold opens the circuit."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2))

        def failing_func():
            raise ValueError("test error")

        # First failure
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.CLOSED

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_blocks_calls(self):
        """Test that open circuit blocks subsequent calls."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

        # Next call should be blocked
        with pytest.raises(CircuitBreakerOpenException):
            cb.call(lambda: "should not execute")

    def test_half_open_recovery(self):
        """Test half-open state and recovery."""
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0.01,  # Very fast recovery for testing
                success_threshold=1,  # Need only 1 success to close
            ),
        )

        def failing_func():
            raise ValueError("test error")

        def successful_func():
            return "success"

        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.02)

        # Next call should attempt recovery (half-open) and succeed
        result = cb.call(successful_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    def test_attempt_recovery_basic(self):
        """Test basic recovery mechanism."""
        cb = CircuitBreaker("test", CircuitBreakerConfig())

        def failing_func():
            raise ValueError("failure")

        # Recovery should fail for failing function
        with pytest.raises(ValueError):
            cb.attempt_recovery(failing_func)

        def success_func():
            return "success"

        # Recovery should succeed for successful function
        result = cb.attempt_recovery(success_func)
        assert result == "success"

    def test_context_manager(self):
        """Test circuit breaker context manager."""
        cb = CircuitBreaker("test", CircuitBreakerConfig())

        with cb.protect():
            pass  # Successful operation

        assert cb.stats.total_calls == 1
        assert cb.stats.successful_calls == 1

    def test_context_manager_with_failure(self):
        """Test circuit breaker context manager with failure."""
        cb = CircuitBreaker("test", CircuitBreakerConfig())

        with pytest.raises(ValueError):
            with cb.protect():
                raise ValueError("test error")

        assert cb.stats.total_calls == 1
        assert cb.stats.failed_calls == 1

    @patch("splurge_unittest_to_pytest.circuit_breaker.HAS_SIGNAL", True)
    @patch("splurge_unittest_to_pytest.circuit_breaker.signal")
    def test_timeout_protection(self, mock_signal):
        """Test timeout protection functionality."""
        mock_signal.SIGALRM = 14  # Mock SIGALRM value
        cb = CircuitBreaker("test", CircuitBreakerConfig(timeout=0.1))

        def slow_func():
            time.sleep(0.2)  # Exceed timeout
            return "done"

        # Mock signal.alarm to simulate timeout
        mock_signal.alarm.side_effect = lambda seconds: (_ for _ in ()).throw(TimeoutError("Operation timed out"))

        with pytest.raises(TimeoutError):
            cb.call(slow_func)

    @patch("splurge_unittest_to_pytest.circuit_breaker.HAS_SIGNAL", False)
    def test_timeout_fallback(self):
        """Test that systems without signal support fall back to no timeout."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(timeout=0.1))

        def slow_func():
            time.sleep(0.2)  # Would exceed timeout on Unix systems with signal
            return "done"

        # Without signal support, should complete normally
        result = cb.call(slow_func)
        assert result == "done"


class TestGlobalRegistry:
    """Test global circuit breaker registry."""

    def test_get_circuit_breaker_creates_new(self):
        """Test getting a circuit breaker creates new instance."""
        cb1 = get_circuit_breaker("test1", CircuitBreakerConfig())
        cb2 = get_circuit_breaker("test2", CircuitBreakerConfig())

        assert cb1.name == "test1"
        assert cb2.name == "test2"
        assert cb1 is not cb2

    def test_get_circuit_breaker_returns_existing(self):
        """Test getting a circuit breaker returns existing instance."""
        config = CircuitBreakerConfig()
        cb1 = get_circuit_breaker("test", config)
        cb2 = get_circuit_breaker("test", config)

        assert cb1 is cb2

    def test_global_registry(self):
        """Test global circuit breaker registry."""
        cb1 = get_circuit_breaker("registry_test1", CircuitBreakerConfig())
        cb2 = get_circuit_breaker("registry_test2", CircuitBreakerConfig())

        # Same name should return same instance
        cb1_again = get_circuit_breaker("registry_test1", CircuitBreakerConfig())
        assert cb1 is cb1_again

        # Different names should return different instances
        assert cb1 is not cb2

        # Test stats retrieval
        stats = get_circuit_breaker_stats("registry_test1")
        assert stats is not None
        assert stats.total_calls == 0  # Initial state

        # Test reset
        reset_circuit_breaker("registry_test1")
        # Should still exist but stats should be reset
        stats_after_reset = get_circuit_breaker_stats("registry_test1")
        assert stats_after_reset is not None


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker functionality."""

    def test_end_to_end_recovery_workflow(self):
        """Test complete recovery workflow."""
        cb = CircuitBreaker(
            "integration_test",
            CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1, success_threshold=1, max_retries=1),
        )

        def unreliable_func():
            # Fail first two times, then succeed
            if cb.stats.total_calls < 2:
                raise RuntimeError("Temporary failure")
            return "success"

        # First two calls should fail and open circuit
        for _i in range(2):
            with pytest.raises(RuntimeError):
                cb.call(unreliable_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.2)

        # Next call should attempt recovery and succeed
        result = cb.call(unreliable_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    def test_stats_persistence_across_states(self):
        """Test that statistics persist correctly across state changes."""
        cb = CircuitBreaker("stats_test", CircuitBreakerConfig(failure_threshold=2))

        def failing_func():
            raise ValueError("fail")

        def success_func():
            return "ok"

        # Record some stats manually
        cb.stats.total_calls = 1
        cb.stats.successful_calls = 1
        cb.stats.failed_calls = 0

        # Fail to change stats
        try:
            cb.call(failing_func)
        except ValueError:
            pass

        assert cb.stats.failed_calls == 1
        assert cb.stats.successful_calls == 1  # Should remain 1
        assert cb.stats.total_calls == 2  # Should be incremented
