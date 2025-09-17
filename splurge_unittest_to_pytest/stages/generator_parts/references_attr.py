"""Detect references to ``self.<attr>`` or a bare attribute name.

Recursive utilities to check whether an expression references
``self.<attr>`` or the bare attribute name. Extracted to make the
logic unit-testable.

Publics:
    references_attribute

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Any

import libcst as cst

DOMAINS = ["generator"]

# Associated domains for this module


def references_attribute(expr: Any, attr_name: str) -> bool:
    """Check whether ``expr`` references ``self.<attr>`` or a bare name.

    The function is defensive about unexpected libcst node shapes and
    returns False when it cannot determine a match. Wrapper objects are
    unwrapped where relevant (for example, AssignTarget wrappers).
    """
    # Accept AssignTarget and similar wrapper objects by unwrapping
    expr = getattr(expr, "target", expr)
    if expr is None or not isinstance(expr, cst.BaseExpression):
        return False
    # Attribute like self.attr or cls.attr
    if isinstance(expr, cst.Attribute):
        if isinstance(expr.attr, cst.Name) and expr.attr.value == attr_name:
            if isinstance(expr.value, cst.Name) and expr.value.value in ("self", "cls"):
                return True
        # recurse into value
        return references_attribute(expr.value, attr_name)
    # Name
    if isinstance(expr, cst.Name):
        return expr.value == attr_name
    # Call: check func and args
    if isinstance(expr, cst.Call):
        if references_attribute(expr.func, attr_name):
            return True
        for a in expr.args:
            if references_attribute(a.value, attr_name):
                return True
        return False
    # Subscript (value and slices)
    if isinstance(expr, cst.Subscript):
        if references_attribute(expr.value, attr_name):
            return True
        for s in expr.slice:
            # SubscriptElement may wrap an Index or Slice; try to extract
            # the underlying expression(s) to inspect.
            inner = getattr(s, "slice", None) or getattr(s, "value", None) or s
            # Unwrap Index -> value
            if (
                getattr(inner, "__class__", None) is not None
                and getattr(inner, "value", None) is not None
                and not isinstance(inner, cst.BaseExpression)
            ):
                inner = getattr(inner, "value", inner)
            # If it's a Slice, inspect lower/upper/step
            if isinstance(inner, cst.Slice):
                for part in (
                    getattr(inner, "lower", None),
                    getattr(inner, "upper", None),
                    getattr(inner, "step", None),
                ):
                    if isinstance(part, cst.BaseExpression) and references_attribute(part, attr_name):
                        return True
                continue
            if isinstance(inner, cst.BaseExpression) and references_attribute(inner, attr_name):
                return True
        return False
    # Binary/Comparison/Boolean ops
    if isinstance(expr, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
        parts: list[cst.BaseExpression] = []
        if hasattr(expr, "left"):
            parts.append(expr.left)
        if hasattr(expr, "right"):
            parts.append(expr.right)
        if hasattr(expr, "comparisons"):
            for comp in expr.comparisons:
                comp_item = getattr(comp, "comparison", None) or getattr(comp, "operator", None)
                if comp_item is not None and isinstance(comp_item, cst.BaseExpression):
                    parts.append(comp_item)
        for p in parts:
            if references_attribute(p, attr_name):
                return True
        return False
    # Tuples/Lists/Sets
    if isinstance(expr, (cst.Tuple, cst.List, cst.Set)):
        for e in expr.elements:
            val = getattr(e, "value", e)
            if isinstance(val, cst.BaseExpression) and references_attribute(val, attr_name):
                return True
        return False
    # default: no reference found
    return False
