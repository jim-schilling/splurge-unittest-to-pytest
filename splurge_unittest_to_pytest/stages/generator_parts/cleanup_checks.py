"""Heuristics to detect simple cleanup statements for the generator.

Identify simple cleanup patterns (assigns or deletes targeting
``self.<attr>``, ``cls.<attr>``, or bare names) so the generator can
emit teardown fixtures.

Publics:
    is_simple_cleanup_statement

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Any

import libcst as cst

DOMAINS = ["generator"]

# Associated domains for this module


def is_simple_cleanup_statement(s: Any, attr: str) -> bool:
    """Detect simple cleanup statements targeting an attribute.

    The function recognizes simple assignment, expression-wrapped
    assignment, and delete-like nodes that target ``self.<attr>``,
    ``cls.<attr>``, or a bare name equal to ``attr``.

    Args:
        s: A libcst statement-like object.
        attr: The attribute name to check for.

    Returns:
        True if the statement is a simple cleanup for ``attr``; False
        otherwise.
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
        # Detect Delete by class name to handle differing libcst representations
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
