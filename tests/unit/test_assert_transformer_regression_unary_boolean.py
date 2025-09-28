import libcst as cst

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


def test_unary_not_wrapping_boolean_and_regression():
    # regression test: ensure unary-not around boolean-and with membership
    # comparisons referencing alias.output is rewritten to caplog form
    src = "assert not (('err' in log.output[0]) and ('x' in log.output[1]))"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    assert "getMessage" in r or "records" in r
