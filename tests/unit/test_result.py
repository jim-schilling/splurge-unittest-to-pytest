"""Tests for the Result system."""

import pytest

from splurge_unittest_to_pytest.result import Result, ResultStatus


def test_result_success():
    """Test successful result creation and access."""
    data = {"key": "value"}
    result = Result.success(data)

    assert result.is_success()
    assert not result.is_error()
    assert result.data == data
    assert result.error is None
    assert result.warnings == []
    assert result.metadata == {}


def test_result_error():
    """Test error result creation and access."""
    error = ValueError("Test error")
    result = Result.failure(error)

    assert result.is_error()
    assert not result.is_success()
    assert result.data is None
    assert result.error == error
    assert result.warnings == []
    assert result.metadata == {}


def test_result_warning():
    """Test warning result creation and access."""
    data = "test data"
    warnings = ["Warning 1", "Warning 2"]
    result = Result.warning(data, warnings)

    assert result.is_warning()
    assert not result.is_error()
    assert result.data == data
    assert result.warnings == warnings
    assert result.metadata == {}


def test_result_skipped():
    """Test skipped result creation and access."""
    metadata = {"reason": "test"}
    result = Result.skipped("Test skip", metadata)

    assert result.is_skipped()
    assert not result.is_error()
    assert result.data is None
    assert result.error is None
    assert result.warnings == []
    assert result.metadata == metadata


def test_result_map_success():
    """Test mapping over successful result."""
    result = Result.success(5)
    mapped = result.map(lambda x: x * 2)

    assert mapped.is_success()
    assert mapped.data == 10


def test_result_map_error():
    """Test mapping over error result."""
    error = ValueError("Original error")
    result = Result.failure(error)
    mapped = result.map(lambda x: x * 2)

    assert mapped.is_error()
    assert mapped.error == error


def test_result_bind_success():
    """Test binding over successful result."""

    def double(x: int) -> Result[int]:
        return Result.success(x * 2)

    result = Result.success(5)
    bound = result.bind(double)

    assert bound.is_success()
    assert bound.data == 10


def test_result_bind_error():
    """Test binding over error result."""

    def double(x: int) -> Result[int]:
        return Result.success(x * 2)

    error = ValueError("Original error")
    result = Result.failure(error)
    bound = result.bind(double)

    assert bound.is_error()
    assert bound.error == error


def test_result_or_else_success():
    """Test or_else with successful result."""
    result = Result.success("data")
    assert result.or_else("default") == "data"


def test_result_or_else_error():
    """Test or_else with error result."""
    result = Result.failure(ValueError("error"))
    assert result.or_else("default") == "default"


def test_result_unwrap_success():
    """Test unwrap with successful result."""
    result = Result.success("data")
    assert result.unwrap() == "data"


def test_result_unwrap_error():
    """Test unwrap with error result raises exception."""
    error = ValueError("Test error")
    result = Result.failure(error)

    with pytest.raises(ValueError, match="Test error"):
        result.unwrap()


def test_result_unwrap_or_success():
    """Test unwrap_or with successful result."""
    result = Result.success("data")
    assert result.unwrap_or("default") == "data"


def test_result_unwrap_or_error():
    """Test unwrap_or with error result."""
    result = Result.failure(ValueError("error"))
    assert result.unwrap_or("default") == "default"


def test_result_to_dict():
    """Test converting result to dictionary."""
    data = {"test": "value"}
    warnings = ["Warning"]
    metadata = {"key": "value"}

    result = Result.warning(data, warnings, metadata)

    result_dict = result.to_dict()
    assert result_dict["status"] == "warning"
    assert result_dict["data"] == data
    assert result_dict["error"] is None
    assert result_dict["warnings"] == warnings
    assert result_dict["metadata"] == metadata


def test_result_string_representation():
    """Test string representation of results."""
    success_result = Result.success("data")
    assert "success" in str(success_result)
    assert "data" in str(success_result)

    error_result = Result.failure(ValueError("test"))
    assert "error" in str(error_result)

    warning_result = Result.warning("data", ["warning"])
    assert "warning" in str(warning_result)

    skipped_result = Result.skipped("reason")
    assert "skipped" in str(skipped_result)
