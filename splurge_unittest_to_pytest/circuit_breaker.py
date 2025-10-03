"""Circuit breaker pattern for transformation robustness.

This module implements circuit breaker patterns to prevent cascading failures
in transformation pipelines and provide fail-fast behavior for problematic inputs.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

# Signal is only available on Unix-like systems
if TYPE_CHECKING or sys.platform != "win32":
    import signal

    HAS_SIGNAL = True
else:
    try:
        import signal

        HAS_SIGNAL = True
    except ImportError:
        signal = None  # type: ignore[assignment]
        HAS_SIGNAL = False

T = TypeVar("T")

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker operation."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 3  # Consecutive failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying half-open
    success_threshold: int = 2  # Successes needed to close from half-open
    timeout: float | None = None  # Max time for individual operations


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open and operation is blocked."""

    def __init__(self, name: str, stats: CircuitBreakerStats):
        self.name = name
        self.stats = stats
        super().__init__(
            f"Circuit breaker '{name}' is open. Stats: {stats.total_calls} calls, "
            f"{stats.failed_calls} failures, {stats.consecutive_failures} consecutive"
        )


class CircuitBreaker:
    """Circuit breaker for protecting transformation operations."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.half_open_successes = 0

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from open to half-open."""
        if self.state != CircuitState.OPEN:
            return False

        if self.stats.last_failure_time is None:
            return True

        return time.time() - self.stats.last_failure_time >= self.config.recovery_timeout

    def _record_success(self) -> None:
        """Record a successful operation."""
        self.stats.total_calls += 1
        self.stats.successful_calls += 1
        self.stats.consecutive_failures = 0
        self.stats.last_success_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.half_open_successes = 0
                logger.info(f"Circuit breaker '{self.name}' closed after successful recovery")

    def _record_failure(self) -> None:
        """Record a failed operation."""
        self.stats.total_calls += 1
        self.stats.failed_calls += 1
        self.stats.consecutive_failures += 1
        self.stats.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_successes = 0
            logger.warning(f"Circuit breaker '{self.name}' reopened after failure in half-open state")
        elif self.state == CircuitState.CLOSED and self.stats.consecutive_failures >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self.stats.consecutive_failures} consecutive failures"
            )

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Any exception raised by the function
        """
        if self.state == CircuitState.OPEN:
            if not self._should_attempt_reset():
                raise CircuitBreakerOpenException(self.name, self.stats)

            # Try half-open
            self.state = CircuitState.HALF_OPEN
            logger.info(f"Circuit breaker '{self.name}' testing recovery (half-open)")

        try:
            if self.config.timeout is not None:
                result = self._call_with_timeout(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._record_success()
            return result

        except Exception:
            self._record_failure()
            raise

    def _call_with_timeout(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call function with timeout protection."""
        # Timeout is only supported on Unix-like systems
        if not HAS_SIGNAL or signal is None:
            # On Windows or systems without signal support, just call the function without timeout
            return func(*args, **kwargs)

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {self.config.timeout} seconds")

        signal.signal(signal.SIGALRM, timeout_handler)  # type: ignore[attr-defined]
        timeout_value = self.config.timeout
        if timeout_value is not None:
            signal.alarm(int(timeout_value))  # type: ignore[attr-defined]
        else:
            signal.alarm(0)  # type: ignore[attr-defined]

        try:
            return func(*args, **kwargs)
        finally:
            signal.alarm(0)  # type: ignore[attr-defined]

    @contextmanager
    def protect(self):
        """Context manager for protecting a block of code.

        Usage:
            with circuit_breaker.protect():
                # Code to protect
                do_something()
        """
        if self.state == CircuitState.OPEN:
            if not self._should_attempt_reset():
                raise CircuitBreakerOpenException(self.name, self.stats)
            self.state = CircuitState.HALF_OPEN

        try:
            yield
            self._record_success()
        except Exception:
            self._record_failure()
            raise


# Global registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name.

    Args:
        name: Unique name for the circuit breaker
        config: Configuration for the circuit breaker

    Returns:
        The circuit breaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def reset_circuit_breaker(name: str) -> None:
    """Reset a circuit breaker to closed state.

    Args:
        name: Name of the circuit breaker to reset
    """
    if name in _circuit_breakers:
        cb = _circuit_breakers[name]
        cb.state = CircuitState.CLOSED
        cb.stats = CircuitBreakerStats()
        cb.half_open_successes = 0
        logger.info(f"Circuit breaker '{name}' manually reset")


def get_circuit_breaker_stats(name: str) -> CircuitBreakerStats | None:
    """Get statistics for a circuit breaker.

    Args:
        name: Name of the circuit breaker

    Returns:
        Statistics for the circuit breaker, or None if not found
    """
    cb = _circuit_breakers.get(name)
    return cb.stats if cb else None
