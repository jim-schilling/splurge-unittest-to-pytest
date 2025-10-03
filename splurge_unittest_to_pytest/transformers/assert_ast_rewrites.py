"""AST-shaped assertion rewrite helpers (stage-1 shim).

This module provides a small, stable surface for pure AST rewrite
helpers extracted from ``assert_transformer``. Initially these are
thin shims that delegate to the original module so the behaviour is
unchanged while we incrementally move implementations.

Do not add new behaviour here; prefer to move code from
``assert_transformer.py`` into this module in follow-up commits.
"""

from typing import Any

import libcst as cst

# Import the original implementations as shims to minimize the diff.
from . import assert_transformer as _orig


def parenthesized_expression(expr: cst.BaseExpression) -> Any:
    """Delegate to the original parenthesized_expression helper."""

    return _orig.parenthesized_expression(expr)


# Expose the dataclass type for callers that use isinstance checks.
ParenthesizedExpression: type[Any] = _orig.ParenthesizedExpression


__all__ = ["parenthesized_expression", "ParenthesizedExpression"]
