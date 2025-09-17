"""Tests for the public API of splurge_unittest_to_pytest.exceptions.

These tests exercise the exception classes and their inheritance so callers
can rely on catching broad or narrow categories. Tests avoid fragile exact
string matches and instead assert membership and isinstance relationships.
"""

from __future__ import annotations

import pytest

from splurge_unittest_to_pytest import exceptions


def test_hierarchy_is_correct():
    # Base class
    assert issubclass(exceptions.ConversionError, exceptions.SplurgeError)
    assert issubclass(exceptions.ParseError, exceptions.ConversionError)
    assert issubclass(exceptions.FileOperationError, exceptions.SplurgeError)

    # File operation specializations
    assert issubclass(exceptions.FileNotFoundError, exceptions.FileOperationError)
    assert issubclass(exceptions.PermissionDeniedError, exceptions.FileOperationError)
    assert issubclass(exceptions.EncodingError, exceptions.FileOperationError)
    assert issubclass(exceptions.BackupError, exceptions.FileOperationError)


@pytest.mark.parametrize(
    "exc_cls, message",
    [
        (exceptions.SplurgeError, "base"),
        (exceptions.ConversionError, "convert fail"),
        (exceptions.ParseError, "parse: bad"),
        (exceptions.FileOperationError, "file op"),
        (exceptions.FileNotFoundError, "missing file"),
        (exceptions.PermissionDeniedError, "no perms"),
        (exceptions.EncodingError, "bad encoding"),
        (exceptions.BackupError, "backup failed"),
    ],
)
def test_exception_str_and_repr_include_message(exc_cls, message):
    # Ensure exceptions accept a message, include it in str/repr, and are
    # instances of the declared class and SplurgeError when appropriate.
    exc = exc_cls(message)

    # isinstance checks
    assert isinstance(exc, exc_cls)
    assert isinstance(exc, exceptions.SplurgeError)

    # str should contain the message
    assert message in str(exc)

    # repr should contain the class name and the message (not exact format)
    r = repr(exc)
    assert exc.__class__.__name__ in r
    assert message in r


def test_can_raise_and_catch_specific_and_broad():
    # Raising ParseError should be catchable as ParseError and ConversionError
    with pytest.raises(exceptions.ParseError):
        raise exceptions.ParseError("boom")

    with pytest.raises(exceptions.ConversionError):
        raise exceptions.ParseError("boom")

    with pytest.raises(exceptions.SplurgeError):
        raise exceptions.ParseError("boom")


def test_default_message_when_empty():
    # When constructed with no args, Exception.__str__ returns empty string.
    exc = exceptions.EncodingError()
    assert isinstance(exc, exceptions.EncodingError)
    assert str(exc) == ""
