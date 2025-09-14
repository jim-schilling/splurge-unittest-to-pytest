"""Heuristics to detect simple cleanup statements used by the generator.

Extracted from stages/generator.py to enable focused testing.
"""

from __future__ import annotations

from typing import Any

import libcst as cst


def is_simple_cleanup_statement(s: Any, attr: str) -> bool:
    """Return True when `s` is a simple cleanup targeting `attr`.

    Accepts Assign, Expr-wrapped Assign, and Delete-like nodes where the
    target is either `self.attr`/`cls.attr` or a bare `attr` name.
    """
    if isinstance(s, cst.SimpleStatementLine) and s.body:
        expr = s.body[0]
        # Accept Assign directly
        if isinstance(expr, cst.Assign):
            target = expr.targets[0].target
            # accept self.attr or cls.attr
            if (
                isinstance(target, cst.Attribute)
                and isinstance(getattr(target, "value", None), cst.Name)
                and getattr(getattr(target, "value", None), "value", None) in ("self", "cls")
            ):
                return True
            # also accept bare name assignment like `value = None`
            if isinstance(target, cst.Name) and target.value == attr:
                return True
        # Or Assign wrapped inside an Expr (some tests construct this shape)
        if isinstance(expr, cst.Expr):
            inner = getattr(expr, "value", None)
            if isinstance(inner, cst.Assign):
                target = inner.targets[0].target
                if (
                    isinstance(target, cst.Attribute)
                    and isinstance(getattr(target, "value", None), cst.Name)
                    and getattr(getattr(target, "value", None), "value", None) in ("self", "cls")
                ):
                    return True
                if isinstance(target, cst.Name) and target.value == attr:
                    return True
        # Detect Delete by class name for compatibility with varying libcst
        cls = getattr(expr, "__class__", None)
        # libcst may expose Delete/Del depending on version; accept both names
        if cls is not None and getattr(cls, "__name__", None) in ("Delete", "Del"):
            for t in getattr(expr, "targets", []):
                targ = getattr(t, "target", t)
                if (
                    isinstance(targ, cst.Attribute)
                    and isinstance(getattr(targ, "value", None), cst.Name)
                    and getattr(getattr(targ, "value", None), "value", None) in ("self", "cls")
                ):
                    return True
    return False
