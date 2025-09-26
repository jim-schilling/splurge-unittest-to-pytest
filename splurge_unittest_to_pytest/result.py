"""Result type for functional error handling.

This module provides a Result[T] type that encapsulates both successful results
and error conditions, enabling functional composition of operations.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class ResultStatus(Enum):
    """Status of a Result operation."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Result(Generic[T]):
    """Immutable result with error handling.

    This class provides functional error handling through method chaining,
    similar to Rust's Result or Haskell's Either types.
    """

    status: ResultStatus
    data: T | None = None
    error: Exception | None = None
    warnings: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate result consistency."""
        if self.status == ResultStatus.SUCCESS and self.error is not None:
            raise ValueError("Success results cannot have errors")
        if self.status == ResultStatus.ERROR and self.data is not None:
            raise ValueError("Error results cannot have data")
        if self.warnings is None:
            object.__setattr__(self, "warnings", [])
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

    @classmethod
    def success(cls, data: T, metadata: dict[str, Any] | None = None) -> "Result[T]":
        """Create a successful result."""
        return cls(status=ResultStatus.SUCCESS, data=data, error=None, metadata=metadata or {})

    @classmethod
    def failure(cls, error: Exception, metadata: dict[str, Any] | None = None) -> "Result[T]":
        """Create an error result."""
        return cls(status=ResultStatus.ERROR, error=error, metadata=metadata or {})

    @classmethod
    def warning(cls, data: T, warnings: list[str], metadata: dict[str, Any] | None = None) -> "Result[T]":
        """Create a result with warnings."""
        return cls(status=ResultStatus.WARNING, data=data, warnings=warnings, metadata=metadata or {})

    @classmethod
    def skipped(cls, reason: str, metadata: dict[str, Any] | None = None) -> "Result[T]":
        """Create a skipped result."""
        return cls(status=ResultStatus.SKIPPED, metadata=metadata or {})

    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.status == ResultStatus.SUCCESS

    def is_error(self) -> bool:
        """Check if result is an error."""
        return self.status == ResultStatus.ERROR

    def is_warning(self) -> bool:
        """Check if result has warnings."""
        return self.status == ResultStatus.WARNING

    def is_skipped(self) -> bool:
        """Check if result was skipped."""
        return self.status == ResultStatus.SKIPPED

    def map(self, func: Callable[[T], R]) -> "Result[R]":
        """Apply function to successful result data.

        Args:
            func: Function to apply to the data

        Returns:
            New Result with transformed data or original error
        """
        if self.is_error():
            return Result[R](
                status=ResultStatus.ERROR, error=self.error, warnings=self.warnings, metadata=self.metadata
            )

        if self.is_skipped():
            return Result[R](status=ResultStatus.SKIPPED, metadata=self.metadata)

        if self.data is None:
            return Result.failure(ValueError("Cannot map over None data"), self.metadata)

        try:
            new_data = func(self.data)
            status = ResultStatus.WARNING if self.warnings else ResultStatus.SUCCESS
            return Result[R](status=status, data=new_data, error=None, warnings=self.warnings, metadata=self.metadata)
        except Exception as e:
            return Result.failure(e, self.metadata)

    def bind(self, func: Callable[[T], "Result[R]"]) -> "Result[R]":
        """Apply function that returns a Result.

        Args:
            func: Function that takes data and returns a Result

        Returns:
            Result from applying the function or original error
        """
        if self.is_error():
            return Result[R](
                status=ResultStatus.ERROR, error=self.error, warnings=self.warnings, metadata=self.metadata
            )

        if self.is_skipped():
            return Result[R](status=ResultStatus.SKIPPED, metadata=self.metadata)

        if self.data is None:
            return Result.failure(ValueError("Cannot bind over None data"), self.metadata)

        try:
            return func(self.data)
        except Exception as e:
            return Result.failure(e, self.metadata)

    def or_else(self, default_value: T) -> T:
        """Get data or return default value.

        Args:
            default_value: Value to return if result is error or skipped

        Returns:
            Data if successful, default_value otherwise
        """
        if self.is_success() and self.data is not None:
            return self.data
        return default_value

    def unwrap(self) -> T:
        """Get data or raise error.

        Returns:
            Data if successful

        Raises:
            Exception: If result is error or skipped
        """
        if self.is_error():
            raise self.error or RuntimeError("Result contains error")
        if self.is_skipped():
            raise RuntimeError("Result was skipped")
        if self.data is None:
            raise RuntimeError("Result contains no data")
        return self.data

    def unwrap_or(self, default_value: T) -> T:
        """Get data or default value.

        Args:
            default_value: Default value to return if no data

        Returns:
            Data if available, default_value otherwise
        """
        if self.is_success() and self.data is not None:
            return self.data
        return default_value

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation.

        Returns:
            Dictionary representation of the result
        """
        return {
            "status": self.status.value,
            "data": self.data,
            "error": str(self.error) if self.error else None,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation of the result."""
        if self.is_success():
            return f"Result(success, data={self.data})"
        elif self.is_error():
            return f"Result(error, error={self.error})"
        elif self.is_warning():
            return f"Result(warning, data={self.data}, warnings={self.warnings})"
        else:
            return f"Result(skipped, metadata={self.metadata})"

    def __repr__(self) -> str:
        """Detailed string representation of the result."""
        return (
            f"Result(status={self.status.value}, "
            f"data={repr(self.data)}, "
            f"error={repr(self.error)}, "
            f"warnings={self.warnings}, "
            f"metadata={self.metadata})"
        )
