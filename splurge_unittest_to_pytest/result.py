"""Result type for functional error handling.

This module provides an immutable ``Result[T]`` type that encapsulates
successful values, warnings, and errors. It enables functional-style
composition with helper methods such as ``map`` and ``bind``.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class ResultStatus(Enum):
    """Enumerates possible statuses for a ``Result``.

    Values include ``SUCCESS``, ``WARNING``, ``ERROR``, and ``SKIPPED``.
    """

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Result(Generic[T]):
    """Immutable result value with structured errors and warnings.

    The class models operation outcomes and provides convenience
    constructors for common cases (``success``, ``failure``,
    ``warning``, ``skipped``) plus helpers for composition.
    """

    status: ResultStatus
    data: T | None = None
    error: Exception | None = None
    warnings: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate internal consistency of the result instance.

        Ensures success results don't carry errors and error results don't
        carry data.
        """
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
        """Create a successful result.

        Args:
            data: Successful value.
            metadata: Optional metadata mapping.

        Returns:
            ``Result`` with ``status==SUCCESS``.
        """
        return cls(status=ResultStatus.SUCCESS, data=data, error=None, metadata=metadata or {})

    @classmethod
    def failure(cls, error: Exception, metadata: dict[str, Any] | None = None) -> "Result[T]":
        """Create an error result.

        Args:
            error: Exception instance describing the failure.
            metadata: Optional metadata mapping.

        Returns:
            ``Result`` with ``status==ERROR``.
        """
        return cls(status=ResultStatus.ERROR, error=error, metadata=metadata or {})

    @classmethod
    def warning(cls, data: T, warnings: list[str], metadata: dict[str, Any] | None = None) -> "Result[T]":
        """Create a result that succeeded with warnings.

        Args:
            data: Value produced by the operation.
            warnings: List of warning messages.
            metadata: Optional metadata mapping.

        Returns:
            ``Result`` with ``status==WARNING``.
        """
        return cls(status=ResultStatus.WARNING, data=data, warnings=warnings, metadata=metadata or {})

    @classmethod
    def skipped(cls, reason: str, metadata: dict[str, Any] | None = None) -> "Result[T]":
        """Create a skipped result.

        Args:
            reason: Explanation for why the operation was skipped.
            metadata: Optional metadata mapping.

        Returns:
            ``Result`` with ``status==SKIPPED``.
        """
        return cls(status=ResultStatus.SKIPPED, metadata=metadata or {})

    def is_success(self) -> bool:
        """Return True when the result is a success."""
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
        """Apply a function to the successful result data.

        Args:
            func: Function to apply to the data.

        Returns:
            A new ``Result`` containing transformed data, or the original
            error result if this result is an error.
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
        """Chain a function that returns a ``Result``.

        Args:
            func: Function that consumes the data and returns a ``Result``.

        Returns:
            The ``Result`` returned by ``func`` or the original error
            result if this result is an error.
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
        """Return data if present or a default value.

        Args:
            default_value: Value to return if the result is an error or
                skipped.

        Returns:
            Data when successful, otherwise ``default_value``.
        """
        if self.is_success() and self.data is not None:
            return self.data
        return default_value

    def unwrap(self) -> T:
        """Return data if successful or raise an exception.

        Returns:
            The successful data value.

        Raises:
            Exception: If the result represents an error or was skipped.
        """
        if self.is_error():
            raise self.error or RuntimeError("Result contains error")
        if self.is_skipped():
            raise RuntimeError("Result was skipped")
        if self.data is None:
            raise RuntimeError("Result contains no data")
        return self.data

    def unwrap_or(self, default_value: T) -> T:
        """Return data if present, otherwise ``default_value``.

        Args:
            default_value: Default value to return if no data is available.

        Returns:
            Data when successful, otherwise ``default_value``.
        """
        if self.is_success() and self.data is not None:
            return self.data
        return default_value

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a dictionary representation.

        Returns:
            A serializable mapping with status, data, error, warnings, and
            metadata.
        """
        return {
            "status": self.status.value,
            "data": self.data,
            "error": str(self.error) if self.error else None,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """Human-friendly string representation of the result."""
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
