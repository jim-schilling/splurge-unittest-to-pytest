"""Helper utilities for method name normalization and pattern matching.

These are extracted from `converter.py` to make them easier to test.
"""

from __future__ import annotations

from typing import Iterable

from .helpers import normalize_method_name


def _pattern_in_name(method_name: str, pattern: str) -> bool:
    """Internal helper: check if a pattern matches the method name according
    to the rules used by the transformer.
    """
    method_lower = method_name.lower()
    method_normalized = normalize_method_name(method_name)
    pattern_lower = pattern.lower()
    return (
        pattern_lower in method_lower
        or pattern_lower in method_normalized
        or normalize_method_name(pattern) in method_normalized
    )


def is_setup_method(method_name: str, patterns: Iterable[str]) -> bool:
    """Return True if the method name matches any of the setup patterns."""
    return any(_pattern_in_name(method_name, p) for p in patterns)


def is_teardown_method(method_name: str, patterns: Iterable[str]) -> bool:
    """Return True if the method name matches any of the teardown patterns."""
    return any(_pattern_in_name(method_name, p) for p in patterns)


def is_test_method(method_name: str, patterns: Iterable[str]) -> bool:
    """Return True if the method name matches any of the test patterns."""
    return any(_pattern_in_name(method_name, p) for p in patterns)
