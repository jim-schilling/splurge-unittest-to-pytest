"""Small helper module for cleanup attribute detection."""

from __future__ import annotations

from typing import Any

import libcst as cst


def references_attribute(expr: Any, attr_name: str) -> bool:
    """Check if an expression references a specific attribute name.

    Mirrors the logic previously defined in the monolithic converter.
    """
    # Direct attribute or name match
    if isinstance(expr, cst.Attribute):
        if expr.attr.value == attr_name:
            return True
        return references_attribute(expr.value, attr_name)
    if isinstance(expr, cst.Name):
        return expr.value == attr_name

    # Calls: inspect func and args
    if isinstance(expr, cst.Call):
        if references_attribute(expr.func, attr_name):
            return True
        for a in expr.args:
            if references_attribute(a.value, attr_name):
                return True
        return False

    # Subscript/indexing
    if isinstance(expr, cst.Subscript):
        if references_attribute(expr.value, attr_name):
            return True
        for s in expr.slice:
            inner = getattr(s, "slice", None) or getattr(s, "value", None) or s
            # Handle Index or SubscriptElement wrappers that may contain expressions
            if isinstance(inner, (cst.Index, cst.SubscriptElement)):
                inner_expr = getattr(inner, "value", getattr(inner, "slice", None))
            else:
                inner_expr = inner
            if isinstance(inner_expr, cst.BaseExpression) and references_attribute(inner_expr, attr_name):
                return True
        return False

    # Binary operations, comparisons, boolean ops
    if isinstance(expr, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
        parts: list[Any] = []
        if hasattr(expr, "left"):
            parts.append(expr.left)
        if hasattr(expr, "right"):
            parts.append(expr.right)
        if hasattr(expr, "comparisons"):
            for comp in expr.comparisons:
                # ComparisonTarget provides 'comparator' as the RHS expression.
                comp_item = getattr(comp, "comparator", None) or getattr(comp, "operator", None)
                if comp_item is not None:
                    parts.append(comp_item)
        for part in parts:
            if isinstance(part, cst.BaseExpression) and references_attribute(part, attr_name):
                return True
        return False

    # Sequences/containers
    if isinstance(expr, (cst.Tuple, cst.List, cst.Set)):
        for e in expr.elements:
            val = getattr(e, "value", e)
            if isinstance(val, cst.BaseExpression) and references_attribute(val, attr_name):
                return True
        return False

    return False
