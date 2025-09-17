"""Utilities to detect simple literal-like :mod:`libcst` expressions.

Extracted from ``stages/generator.py`` to enable focused testing and reuse
by generator helper components.
"""

from __future__ import annotations

from typing import Optional

import libcst as cst

DOMAINS = ["generator", "literals"]

# Associated domains for this module


def is_literal(expr: Optional[cst.BaseExpression]) -> bool:
    """Return True for expressions considered literal for generator logic.

    Numeric and simple string literals are treated as literals. Bare
    :class:`libcst.Name` nodes are treated as non-literals so variable
    references are handled via local bindings.
    """
    if expr is None:
        return False
    # include common container literals as "literal enough" for our
    # purposes (tuples/lists/sets/dicts) so fixtures holding those
    # values can be returned directly where appropriate.
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString, cst.Tuple, cst.List, cst.Set, cst.Dict))
