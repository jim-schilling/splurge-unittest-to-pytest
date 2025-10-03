"""Fallback heuristics for assertion transformations.

These functions may rely on string/regex heuristics and are separated
to make it easier to gate them behind feature flags in follow-up
refactors.
"""

from . import assert_transformer as _orig


def parenthesized_expression_shim(expr):
    # Simple shim to demonstrate import surface for tests.
    return _orig.parenthesized_expression(expr)


__all__ = ["parenthesized_expression_shim"]
