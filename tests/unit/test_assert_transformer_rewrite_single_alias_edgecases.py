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


def test_nested_subscript_and_slice():
    src = "assert 'x' in log.output[0][1:]"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    assert "getMessage" in r


def test_combined_boolean_and_membership():
    src = "assert ('err' in log.output[0]) and (len(log.output) > 0)"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    # The helper currently rewrites membership and len-sides individually; ensure at least one appearance rewritten
    r = repr(new if new is not None else a)
    assert "caplog" in r


def test_rhs_equality_with_subscript_on_lhs():
    src = "assert log.output[1] == other_var"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    assert "getMessage" in r


def test_non_output_attribute_unchanged():
    src = "assert log.something_else == 'ok'"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    assert new is None


def test_double_subscript_index():
    src = "assert len(log.output[0][0]) == 1"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
