"""Unit tests for transformers._caplog_helpers.

Covers typical shapes and edge-cases for the small pure helpers.
"""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.transformers._caplog_helpers import (
    AliasOutputAccess,
    build_caplog_records_expr,
    build_get_message_call,
    extract_alias_output_slices,
)


def _parse_expr(src: str) -> cst.BaseExpression:
    """Parse an expression string and return the expression node."""
    module = cst.parse_module(src)
    # the expression will be the first statement's value
    stmt = module.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    expr_stmt = stmt.body[0]
    assert isinstance(expr_stmt, cst.Expr)
    return expr_stmt.value


def test_extract_alias_output_simple():
    expr = _parse_expr("alias.output")
    access = extract_alias_output_slices(expr)
    assert isinstance(access, AliasOutputAccess)
    assert access.alias_name == "alias"
    assert access.slices == ()


def test_extract_alias_output_with_slices():
    expr = _parse_expr("alias.output[0][1]")
    access = extract_alias_output_slices(expr)
    assert isinstance(access, AliasOutputAccess)
    assert access.alias_name == "alias"
    assert len(access.slices) == 2


def test_extract_alias_records_simple():
    expr = _parse_expr("alias.records")
    access = extract_alias_output_slices(expr)
    assert isinstance(access, AliasOutputAccess)
    assert access.alias_name == "alias"


def test_extract_alias_output_negative():
    expr = _parse_expr("not_alias.someattr")
    assert extract_alias_output_slices(expr) is None


def test_build_caplog_and_getmessage_call():
    expr = _parse_expr("alias.output[0]")
    access = extract_alias_output_slices(expr)
    assert access is not None
    caplog_expr = build_caplog_records_expr(access)
    # Expect 'caplog.records' as the base attribute
    assert isinstance(caplog_expr, cst.Subscript)
    # Build the getMessage call and ensure it's a Call node
    getmsg = build_get_message_call(access)
    assert isinstance(getmsg, cst.Call)
