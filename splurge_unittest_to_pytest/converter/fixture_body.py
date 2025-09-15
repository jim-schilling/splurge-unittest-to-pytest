"""Helpers to construct fixture function bodies for fixtures created from setUp/tearDown."""

from __future__ import annotations

from typing import Iterable

import libcst as cst

from .value_checks import is_simple_fixture_value
from .fixture_builder import replace_attr_references_in_statements

DOMAINS = ["converter", "fixtures"]

# Associated domains for this module


def build_fixture_body(
    attr_name: str, value_expr: cst.BaseExpression, cleanup_statements: Iterable[cst.BaseStatement]
) -> cst.IndentedBlock:
    """Return an IndentedBlock suitable for a fixture function body.

    If `value_expr` is a simple literal (int/float/string) the body will yield it
    directly followed by cleanup statements. Otherwise the value will be assigned
    to a local name and yielded, and cleanup statements will be rewritten to refer
    to the local name.
    """
    cleanup_list = list(cleanup_statements)

    if is_simple_fixture_value(value_expr):
        yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=value_expr))])
        body = cst.IndentedBlock(body=[yield_stmt] + cleanup_list)
        return body

    value_name = f"_{attr_name}_value"
    value_assign = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(value_name))],
                value=value_expr,
            )
        ]
    )
    yield_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Yield(value=cst.Name(value_name)))])

    safe_cleanup = replace_attr_references_in_statements(cleanup_list, attr_name, value_name)

    body = cst.IndentedBlock(body=[value_assign, yield_stmt] + safe_cleanup)
    return body
