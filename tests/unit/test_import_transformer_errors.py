"""Error-coverage tests for import_transformer helpers.

These tests purposely trigger parse errors or attribute-access errors to
exercise the conservative error-handling branches in the helpers.
"""

from __future__ import annotations

from splurge_unittest_to_pytest.transformers.import_transformer import (
    add_pytest_imports,
    remove_unittest_imports_if_unused,
)


def test_add_pytest_imports_returns_original_on_parse_error() -> None:
    # Provide clearly invalid Python that will cause libcst parser to raise
    code = "def bad:("
    out = add_pytest_imports(code)
    # Should return original code unchanged on parse error
    assert out == code


class _BrokenAttr:
    # Accessing attributes raises an exception to simulate a broken transformer
    def __getattr__(self, name: str):
        raise RuntimeError("boom")


def test_add_pytest_imports_handles_broken_transformer_attrs() -> None:
    src = "import os\n\nprint(1)\n"
    transformer = _BrokenAttr()

    # Current implementation does not guard getattr calls for transformer
    # attribute access; verify that attribute access errors propagate.
    import pytest

    with pytest.raises(RuntimeError):
        _ = add_pytest_imports(src, transformer=transformer)


def test_remove_unittest_imports_handles_parse_error() -> None:
    code = "class X:("
    out = remove_unittest_imports_if_unused(code)
    assert out == code
