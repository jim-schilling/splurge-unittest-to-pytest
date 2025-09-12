import libcst as cst

from splurge_unittest_to_pytest.converter import assertions


def _wrap_assert(node: cst.Assert) -> str:
    return cst.Module(body=[node]).code


def test_assert_equal_basic():
    args = [cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("2"))]
    node = assertions._assert_equal(args)
    code = _wrap_assert(node)
    assert "assert 1 == 2" in code


def test_assert_not_equal_basic():
    args = [cst.Arg(value=cst.Name("a")), cst.Arg(value=cst.Name("b"))]
    node = assertions._assert_not_equal(args)
    assert "!=" in _wrap_assert(node)


def test_assert_true_and_false():
    t = assertions._assert_true([cst.Arg(value=cst.Name("cond"))])
    f = assertions._assert_false([cst.Arg(value=cst.Name("cond"))])
    assert "assert cond" in _wrap_assert(t)
    assert "assert not cond" in _wrap_assert(f)


def test_assert_is_none_literal_returns_none():
    res = assertions._assert_is_none([cst.Arg(value=cst.Integer("1"))])
    assert res is None


def test_assert_is_none_non_literal():
    res = assertions._assert_is_none([cst.Arg(value=cst.Name("x"))])
    assert "is None" in _wrap_assert(res)


def test_assert_is_not_none():
    res = assertions._assert_is_not_none([cst.Arg(value=cst.Name("x"))])
    assert "is not None" in _wrap_assert(res)


def test_assert_in_and_not_in():
    a = assertions._assert_in([cst.Arg(value=cst.Name("a")), cst.Arg(value=cst.Name("b"))])
    b = assertions._assert_not_in([cst.Arg(value=cst.Name("a")), cst.Arg(value=cst.Name("b"))])
    assert "in b" in _wrap_assert(a) or "in b" in _wrap_assert(a)
    assert "not in" in _wrap_assert(b)


def test_isinstance_variants():
    ok = assertions._assert_is_instance([cst.Arg(value=cst.Name("x")), cst.Arg(value=cst.Name("T"))])
    nok = assertions._assert_not_is_instance([cst.Arg(value=cst.Name("x")), cst.Arg(value=cst.Name("T"))])
    assert "isinstance(x, T)" in _wrap_assert(ok)
    assert "not isinstance" in _wrap_assert(nok)
