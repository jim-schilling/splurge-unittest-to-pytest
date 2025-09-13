"""Inspect simple statements for attribute references."""

from __future__ import annotations


import libcst as cst

from .cleanup_checks import references_attribute


def simple_stmt_references_attribute(stmt: cst.SimpleStatementLine, attr_name: str) -> bool:
    """Return True if the given simple statement line references attr_name.

    Handles Expr(Call(...)), Expr(...), and Assign within a SimpleStatementLine.
    """
    if not stmt.body:
        return False
    expr = stmt.body[0]
    if isinstance(expr, cst.Expr) and isinstance(expr.value, cst.Call):
        call = expr.value
        if references_attribute(call.func, attr_name):
            return True
        for arg in call.args:
            if references_attribute(arg.value, attr_name):
                return True
        return False
    if isinstance(expr, cst.Expr):
        return references_attribute(expr.value, attr_name)
    if isinstance(expr, cst.Assign):
        for target in expr.targets:
            target_expr = getattr(target, "target", target)
            if references_attribute(target_expr, attr_name):
                return True
    return False
