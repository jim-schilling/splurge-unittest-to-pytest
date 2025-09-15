"""Small helpers to classify expressions used when building fixtures."""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter", "validation"]

# Associated domains for this module


def is_simple_fixture_value(expr: cst.BaseExpression) -> bool:
    """Return True when an expression is a simple literal that can be yielded
    directly from a fixture without binding to a local variable.

    Currently treats integers, floats and simple strings as simple values.
    """
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString))
