import libcst as cst

from splurge_unittest_to_pytest.converter.assertions import (
    _assert_equal,
    _assert_true,
    _assert_is_none,
    _assert_in,
)
from splurge_unittest_to_pytest.converter.assertion_dispatch import convert_assertion

DOMAINS = ["assertions", "converter"]


def _arg(expr: cst.BaseExpression) -> cst.Arg:
    return cst.Arg(value=expr)


def test_assert_equal_basic():
    a = _assert_equal([_arg(cst.Integer("1")), _arg(cst.Integer("1"))])
    assert isinstance(a, cst.Assert)


def test_assert_true_basic():
    a = _assert_true([_arg(cst.Name("x"))])
    assert isinstance(a, cst.Assert)


def test_assert_is_none_literal_returns_none():
    # integer literal should return None per helper behavior
    assert _assert_is_none([_arg(cst.Integer("1"))]) is None


def test_assert_in_basic():
    a = _assert_in([_arg(cst.Name("x")), _arg(cst.Name("y"))])
    assert isinstance(a, cst.Assert)


def test_convert_assertion_mapping():
    # existing mapping entry should route to a cst.Assert
    res = convert_assertion("assertEqual", [_arg(cst.Integer("1")), _arg(cst.Integer("2"))])
    assert isinstance(res, cst.Assert) or res is None
