"""Tests for `converter.cleanup.extract_relevant_cleanup` covering multiple statement shapes."""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup import extract_relevant_cleanup


def test_simple_statement_line_match():
    stmts = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])]
    matched = extract_relevant_cleanup(stmts, "myfile")
    assert matched and isinstance(matched[0], cst.SimpleStatementLine)


def test_if_test_expression_direct_match():
    # If test directly references attr
    if_node = cst.If(test=cst.Name("myfile"), body=cst.IndentedBlock(body=[cst.Pass()]))
    matched = extract_relevant_cleanup([if_node], "myfile")
    assert matched and matched[0] is if_node


def test_if_inner_body_match_returns_enclosing_if():
    inner = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])
    if_node = cst.If(test=cst.Name("x"), body=cst.IndentedBlock(body=[inner]))
    matched = extract_relevant_cleanup([if_node], "myfile")
    # should return the If itself to preserve context
    assert matched and matched[0] is if_node


def test_nested_orelse_if_replacement():
    inner = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])
    nested_if = cst.If(test=cst.Name("y"), body=cst.IndentedBlock(body=[inner]))
    outer = cst.If(test=cst.Name("z"), body=cst.IndentedBlock(body=[cst.Pass()]), orelse=nested_if)
    matched = extract_relevant_cleanup([outer], "myfile")
    assert matched and matched[0] is outer


def test_indented_block_scans_inner_statements():
    inner = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])
    block = cst.IndentedBlock(body=[cst.Pass(), inner])
    matched = extract_relevant_cleanup([block], "myfile")
    assert matched and matched[0] is inner
