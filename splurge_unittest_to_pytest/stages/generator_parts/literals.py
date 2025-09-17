"""Utilities to detect simple literal-like libcst expressions.

Small helpers used by the generator to determine whether an expression is
considered a literal for emission decisions.
"""

from __future__ import annotations

from typing import Optional

import libcst as cst

DOMAINS = ["generator", "literals"]

# Associated domains for this module


def is_literal(expr: Optional[cst.BaseExpression]) -> bool:
    """Determine whether an expression should be treated as a literal.

    Numeric and simple string literals are treated as literals. Container
    literals (tuple/list/set/dict) are also accepted for generator
    decisions. Bare Name nodes are considered non-literals so variable
    references are handled via local bindings.

    Args:
        expr: A libcst expression node or ``None``.

    Returns:
        True when ``expr`` is considered literal-like for generator
        emission decisions, otherwise False.
    """
    if expr is None:
        return False
    # include common container literals as "literal enough" for our
    # purposes (tuples/lists/sets/dicts) so fixtures holding those
    # values can be returned directly where appropriate.
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString, cst.Tuple, cst.List, cst.Set, cst.Dict))
