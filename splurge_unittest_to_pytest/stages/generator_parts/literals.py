"""Small utility to detect simple 'literal-ish' libcst expressions.

Extracted from stages/generator.py so it can be unit-tested independently
and reused by other generator helpers.
"""

from __future__ import annotations

from typing import Optional

import libcst as cst


def is_literal(expr: Optional[cst.BaseExpression]) -> bool:
    """Return True for true literals (numbers and simple strings).

    We treat bare Name nodes as non-literals so that references to
    variables are handled consistently by binding to locals.
    """
    if expr is None:
        return False
    # include common container literals as "literal enough" for our
    # purposes (tuples/lists/sets/dicts) so fixtures holding those
    # values can be returned directly where appropriate.
    return isinstance(expr, (cst.Integer, cst.Float, cst.SimpleString, cst.Tuple, cst.List, cst.Set, cst.Dict))
