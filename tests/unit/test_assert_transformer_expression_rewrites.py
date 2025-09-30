import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    _rewrite_comparison,
    _rewrite_expression,
    _rewrite_unary_operation,
    rewrite_single_alias_assert,
)


def _expr(source: str) -> cst.BaseExpression:
    return cst.parse_expression(source)


def _render(expr: cst.BaseExpression) -> str:
    module = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=expr)])])
    return module.code.strip()


def test_rewrite_comparison_applies_multiple_patterns() -> None:
    comparison = _expr("len(log.output) == log.output[0]")
    assert isinstance(comparison, cst.Comparison)

    rewritten = _rewrite_comparison(comparison, "log")
    assert rewritten is not None

    assert _render(rewritten.left) == "len(caplog.records)"
    assert _render(rewritten.comparisons[0].comparator) == "caplog.records[0].getMessage()"


def test_rewrite_expression_handles_boolean_operation() -> None:
    expr = _expr("'warn' in log.output[0] and len(log.output) == 1")
    assert isinstance(expr, cst.BooleanOperation)

    rewritten = _rewrite_expression(expr, "log")
    assert rewritten is not None

    rendered = _render(rewritten)
    assert "caplog.records[0].getMessage()" in rendered
    assert "len(caplog.records)" in rendered


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "'warn' in log.output[1]['msg']",
            "caplog.records[1]['msg'].getMessage()",
        ),
        (
            "len(log.output[2]['debug']) == 3",
            "len(caplog.records[2]['debug'])",
        ),
    ],
)
def test_rewrite_expression_handles_nested_slices(source: str, expected: str) -> None:
    expr = _expr(source)
    rewritten = _rewrite_expression(expr, "log")

    assert rewritten is not None
    assert expected in _render(rewritten)


def test_rewrite_expression_returns_none_for_other_alias() -> None:
    expr = _expr("'warn' in other.output[0]")
    rewritten = _rewrite_expression(expr, "log")

    assert rewritten is None


def test_rewrite_unary_operation_parenthesized_membership() -> None:
    unary = _expr("not ('bad' in log.output[0])")
    assert isinstance(unary, cst.UnaryOperation)

    rewritten_unary = _rewrite_unary_operation(unary, "log")
    assert rewritten_unary is not None
    assert _render(rewritten_unary) == "not caplog.records[0].getMessage()"


def test_rewrite_unary_operation_returns_none_when_unhandled() -> None:
    unary = _expr("not some_other_alias.output")
    assert isinstance(unary, cst.UnaryOperation)

    rewritten_unary = _rewrite_unary_operation(unary, "log")
    assert rewritten_unary is None


def test_rewrite_single_alias_assert_with_nested_boolean() -> None:
    module = cst.parse_module(
        """
assert not ('err' in log.output[0] and len(log.output) == 1)
"""
    )
    stmt = module.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    assert isinstance(stmt.body[0], cst.Assert)

    rewritten = rewrite_single_alias_assert(stmt.body[0], "log")
    assert rewritten is not None

    rendered = _render(rewritten.test)
    assert "caplog.records[0].getMessage()" in rendered
    assert "len(caplog.records)" in rendered


def test_rewrite_single_alias_assert_returns_none_for_unrelated_alias() -> None:
    module = cst.parse_module("assert 'warn' in other.output[0]")
    stmt = module.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    assert isinstance(stmt.body[0], cst.Assert)

    rewritten = rewrite_single_alias_assert(stmt.body[0], "log")
    assert rewritten is None


def test_rewrite_expression_handles_chained_booleans() -> None:
    expr = _expr("'warn' in log.output[0] and ('info' in log.output[1] or len(log.output) == 2)")
    assert isinstance(expr, cst.BooleanOperation)

    rewritten = _rewrite_expression(expr, "log")
    assert rewritten is not None

    rendered = _render(rewritten)
    assert "caplog.records[0].getMessage()" in rendered
    assert "caplog.records[1].getMessage()" in rendered
    assert "len(caplog.records)" in rendered
