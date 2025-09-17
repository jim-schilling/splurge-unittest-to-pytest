"""Tests for cleanup_checks.references_attribute and cleanup_inspect.simple_stmt_references_attribute."""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter.cleanup_checks import references_attribute
from splurge_unittest_to_pytest.converter.cleanup_inspect import simple_stmt_references_attribute


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

    # Expr(Call) with arg
    call = cst.Call(func=cst.Name("f"), args=[cst.Arg(value=cst.Name("myfile"))])
    stmt = cst.SimpleStatementLine(body=[cst.Expr(value=call)])
    assert simple_stmt_references_attribute(stmt, "myfile")

    # Expr non-call
    stmt2 = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])
    assert simple_stmt_references_attribute(stmt2, "myfile")

    # Assign target refers to attr
    assign = cst.SimpleStatementLine(
        body=[cst.Assign(targets=[cst.AssignTarget(target=cst.Name("myfile"))], value=cst.Name("x"))]
    )
    assert simple_stmt_references_attribute(assign, "myfile")
