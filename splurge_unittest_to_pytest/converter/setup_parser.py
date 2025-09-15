"""Helpers to parse unittest setUp assignments."""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter"]

# Associated domains for this module


def parse_setup_assignments(node: cst.FunctionDef) -> dict[str, cst.BaseExpression]:
    """Parse a setUp function to extract assignments to self.<attr>.

    Returns a dict mapping attribute name -> assigned expression.
    """
    assignments: dict[str, cst.BaseExpression] = {}
    for stmt in node.body.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            if len(stmt.body) > 0:
                expr = stmt.body[0]
                if isinstance(expr, cst.Assign):
                    if (
                        len(expr.targets) == 1
                        and isinstance(expr.targets[0].target, cst.Attribute)
                        and isinstance(expr.targets[0].target.value, cst.Name)
                        and expr.targets[0].target.value.value == "self"
                    ):
                        attr_name = expr.targets[0].target.attr.value
                        assignments[attr_name] = expr.value
    return assignments
