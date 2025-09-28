import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    rewrite_single_alias_assert,
)


def _parse_assert(src: str) -> cst.BaseSmallStatement:
    mod = cst.parse_module(src)
    stmt = mod.body[0]
    if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Assert):
        return stmt.body[0]
    if isinstance(stmt, cst.Assert):
        return stmt
    raise RuntimeError("unexpected parse")


def test_deeply_nested_boolean_and_parentheses():
    src = "assert (('err' in log.output[0]) and ((len(log.output) > 0) or ('x' in log.output[1])))"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    # ensure at least one getMessage or records access is present
    assert "getMessage" in r or "records" in r


def test_unary_not_parenthesized_comparison():
    src = "assert not (\n    'err' in log.output[0]\n)"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r


def test_deep_subscript_chain_rewrite_len():
    src = "assert len(log.output[0][1][2][3]) == 4"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r


def test_unary_not_wrapping_boolean_and_parentheses():
    # not (( 'err' in log.output[0] ) and ('x' in log.output[1]))
    src = "assert not (('err' in log.output[0]) and ('x' in log.output[1]))"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r


def test_unary_not_wrapping_boolean_or_no_extra_parens():
    # not ( 'err' in log.output[0] or 'x' in log.output[1] )
    src = "assert not ('err' in log.output[0] or 'x' in log.output[1])"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
