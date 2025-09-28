import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    rewrite_single_alias_assert,
)


def _parse_assert(src: str) -> cst.BaseSmallStatement:
    mod = cst.parse_module(src)
    # return first statement inside module
    stmt = mod.body[0]
    # if it's a SimpleStatementLine with an Assert inside, return that Assert
    if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Assert):
        return stmt.body[0]
    if isinstance(stmt, cst.Assert):
        return stmt
    raise RuntimeError("unexpected parse")


def test_rewrite_len_subscript():
    src = "assert len(log.output[0]) == 2"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    assert "records" in r


def test_rewrite_membership_getmessage():
    src = "assert 'err' in log.output[0]"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    assert "getMessage" in r


def test_rewrite_equality_rhs_getmessage():
    src = "assert log.output[0] == 'bad'"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    assert "getMessage" in r


def test_rewrite_equality_lhs_records():
    src = "assert len(log.output) == 3"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    r = repr(new if new is not None else a)
    assert "caplog" in r
    # for non-subscripted alias.output, expect records used (no getMessage on the whole records)
    assert "records" in r


def test_preserve_no_rewrite():
    src = "assert 1 == 1"
    a = _parse_assert(src)
    new = rewrite_single_alias_assert(a, "log")
    assert new is None
