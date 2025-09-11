"""Cleanup analysis helpers extracted from the main transformer.

These are pure functions that inspect libcst statement/expression nodes to
determine whether cleanup statements reference a given attribute name.
"""
from typing import Any, List

import libcst as cst


def references_attribute(expr: Any, attr_name: str) -> bool:
    """Check if an expression references a specific attribute name.

    Mirrors the logic previously defined as a method on the transformer.
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
            inner = getattr(s, 'slice', None) or getattr(s, 'value', None) or s
            # Handle Index or SubscriptElement wrappers that may contain expressions
            if isinstance(inner, (cst.Index, cst.SubscriptElement)):
                inner_expr = getattr(inner, 'value', getattr(inner, 'slice', None))
            else:
                inner_expr = inner
            if isinstance(inner_expr, cst.BaseExpression) and references_attribute(inner_expr, attr_name):
                return True
        return False

    # Binary operations, comparisons, boolean ops
    if isinstance(expr, (cst.BinaryOperation, cst.Comparison, cst.BooleanOperation)):
        parts: list[Any] = []
        if hasattr(expr, 'left'):
            parts.append(expr.left)
        if hasattr(expr, 'right'):
            parts.append(expr.right)
        if hasattr(expr, 'comparisons'):
            for comp in expr.comparisons:
                comp_item = getattr(comp, 'comparison', None) or getattr(comp, 'operator', None)
                if comp_item is not None:
                    parts.append(comp_item)
        for part in parts:
            if isinstance(part, cst.BaseExpression) and references_attribute(part, attr_name):
                return True
        return False

    # Sequences/containers
    if isinstance(expr, (cst.Tuple, cst.List, cst.Set)):
        for e in expr.elements:
            val = getattr(e, 'value', e)
            if isinstance(val, cst.BaseExpression) and references_attribute(val, attr_name):
                return True
        return False

    return False


def extract_relevant_cleanup(cleanup_statements: List[Any], attr_name: str) -> List[Any]:
    """Return a list of cleanup statements that reference the given attribute.

    The implementation scans common statement shapes (Expr with Call, Assign,
    If blocks, IndentedBlock) and returns statements that reference attr_name.
    """
    relevant_statements: List[Any] = []

    def inspect_stmt(s: cst.BaseStatement) -> None:
        # Expr(Call(...)) with attribute method call or arg referencing attr
        if isinstance(s, cst.SimpleStatementLine) and s.body:
            expr = s.body[0]
            if isinstance(expr, cst.Expr) and isinstance(expr.value, cst.Call):
                call = expr.value
                func = call.func
                if isinstance(func, cst.Attribute) and references_attribute(func.value, attr_name):
                    relevant_statements.append(s)
                    return
                for arg in call.args:
                    if references_attribute(arg.value, attr_name):
                        relevant_statements.append(s)
                        return
            elif isinstance(expr, cst.Expr):
                # Generic expression (e.g., Subscript, Name, Attribute) may reference the attribute
                if references_attribute(expr.value, attr_name):
                    relevant_statements.append(s)
                    return
            elif isinstance(expr, cst.Assign):
                for target in expr.targets:
                    target_expr = getattr(target, 'target', target)
                    if references_attribute(target_expr, attr_name):
                        relevant_statements.append(s)
                        return

        # If statements: test/body/orelse
        if isinstance(s, cst.If):
            if references_attribute(s.test, attr_name):
                relevant_statements.append(s)
                return
            for inner in getattr(s.body, 'body', []):
                inspect_stmt(inner)
                if relevant_statements and relevant_statements[-1] is inner:
                    return
            orelse = getattr(s, 'orelse', None)
            if orelse:
                if isinstance(orelse, cst.IndentedBlock):
                    for inner in getattr(orelse, 'body', []):
                        inspect_stmt(inner)
                        if relevant_statements and relevant_statements[-1] is inner:
                            return
                elif isinstance(orelse, cst.If):
                    inspect_stmt(orelse)
                    if relevant_statements and relevant_statements[-1] is orelse:
                        return

        # IndentedBlock: inspect contained statements
        if isinstance(s, cst.IndentedBlock):
            for inner in getattr(s, 'body', []):
                inspect_stmt(inner)
                if relevant_statements and relevant_statements[-1] is inner:
                    return

    for stmt in cleanup_statements:
        inspect_stmt(stmt)

    return relevant_statements
