"""Small helpers to classify expressions used when building fixtures.

This module exposes predicate helpers used by the generator to decide when
an expression is 'literal-like' and safe to embed into generated fixture
annotations or return values.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter", "validation"]

# Associated domains for this module


def is_simple_fixture_value(expr: cst.BaseExpression) -> bool:
    """Return True when an expression is a simple literal that can be yielded.

    Args:
        expr: A :class:`libcst.BaseExpression` to classify.

    Returns:
        ``True`` when ``expr`` is a simple literal (integers, floats, simple
        strings), otherwise ``False``.
    """
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString))
