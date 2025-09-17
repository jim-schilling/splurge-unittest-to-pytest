"""Tests for `converter.cleanup.extract_relevant_cleanup` covering multiple statement shapes."""

from __future__ import annotations
import libcst as cst
from splurge_unittest_to_pytest.converter.cleanup import extract_relevant_cleanup
from splurge_unittest_to_pytest.converter.cleanup_checks import references_attribute
from splurge_unittest_to_pytest.converter.cleanup_inspect import simple_stmt_references_attribute


def test_simple_statement_line_match():
    stmts = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])]
    matched = extract_relevant_cleanup(stmts, "myfile")
    assert matched and isinstance(matched[0], cst.SimpleStatementLine)


def test_if_test_expression_direct_match():
    if_node = cst.If(test=cst.Name("myfile"), body=cst.IndentedBlock(body=[cst.Pass()]))
    matched = extract_relevant_cleanup([if_node], "myfile")
    assert matched and matched[0] is if_node


def test_if_inner_body_match_returns_enclosing_if():
    inner = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])
    if_node = cst.If(test=cst.Name("x"), body=cst.IndentedBlock(body=[inner]))
    matched = extract_relevant_cleanup([if_node], "myfile")
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


def test_references_attribute_on_attribute_and_name():
    a = cst.Attribute(value=cst.Name("self"), attr=cst.Name("myfile"))
    assert references_attribute(a, "myfile")
    n = cst.Name("myfile")
    assert references_attribute(n, "myfile")


def test_references_in_call_and_args():
    call = cst.Call(func=cst.Name("make"), args=[cst.Arg(value=cst.Name("myfile"))])
    assert references_attribute(call, "myfile")
    call2 = cst.Call(func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("make")), args=[])
    assert not references_attribute(call2, "myfile")


def test_references_in_subscript_and_container():
    sub = cst.Subscript(value=cst.Name("arr"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("myfile")))])
    assert references_attribute(sub, "myfile")
    tup = cst.Tuple(elements=[cst.Element(value=cst.Name("x")), cst.Element(value=cst.Name("myfile"))])
    assert references_attribute(tup, "myfile")


def test_references_in_binary_and_comparison():
    binop = cst.BinaryOperation(left=cst.Name("a"), operator=cst.Add(), right=cst.Name("myfile"))
    assert references_attribute(binop, "myfile")
    comp = cst.Comparison(
        left=cst.Name("a"), comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Name("myfile"))]
    )
    assert references_attribute(comp, "myfile")


def test_simple_stmt_inspect_empty_and_various():
    empty = cst.SimpleStatementLine(body=[])
    assert not simple_stmt_references_attribute(empty, "myfile")
    call = cst.Call(func=cst.Name("f"), args=[cst.Arg(value=cst.Name("myfile"))])
    stmt = cst.SimpleStatementLine(body=[cst.Expr(value=call)])
    assert simple_stmt_references_attribute(stmt, "myfile")
    stmt2 = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])
    assert simple_stmt_references_attribute(stmt2, "myfile")
    assign = cst.SimpleStatementLine(
        body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name("myfile"))], value=cst.Name("x"))]
    )
    assert simple_stmt_references_attribute(assign, "myfile")
