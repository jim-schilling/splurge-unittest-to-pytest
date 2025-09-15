import libcst as cst

from splurge_unittest_to_pytest.converter import assertions

DOMAINS = ["core"]


def _a(expr: str) -> cst.Arg:
    return cst.Arg(value=cst.parse_expression(expr))


def test_equal_and_not_equal():
    a = _a("1")
    b = _a("2")
    eq = assertions._assert_equal([a, b])
    assert isinstance(eq, cst.Assert)
    assert isinstance(eq.test, cst.Comparison)

    neq = assertions._assert_not_equal([a, b])
    assert isinstance(neq, cst.Assert)
    assert isinstance(neq.test, cst.Comparison)


def test_true_and_false():
    a = _a("x")
    t = assertions._assert_true([a])
    assert isinstance(t, cst.Assert)
    assert isinstance(t.test, cst.BaseExpression)

    f = assertions._assert_false([a])
    assert isinstance(f, cst.Assert)
    assert isinstance(f.test, cst.UnaryOperation)


def test_is_none_and_is_not_none_literal_behavior():
    lit = _a("1")
    # literal should return None to avoid '1 is None'
    assert assertions._assert_is_none([lit]) is None

    # non-literal should return an Assert with Is comparison
    expr = _a("x")
    an = assertions._assert_is_none([expr])
    assert isinstance(an, cst.Assert)
    assert isinstance(an.test, cst.Comparison)

    not_none = assertions._assert_is_not_none([expr])
    assert isinstance(not_none, cst.Assert)
    assert isinstance(not_none.test, cst.Comparison)


def test_in_not_in_and_isinstance_variants():
    x = _a("x")
    seq = _a("seq")
    ai = assertions._assert_in([x, seq])
    assert isinstance(ai, cst.Assert)
    assert isinstance(ai.test, cst.Comparison)

    ani = assertions._assert_not_in([x, seq])
    assert isinstance(ani, cst.Assert)
    assert isinstance(ani.test, cst.Comparison)

    obj = _a("o")
    klass = _a("K")
    isinst = assertions._assert_is_instance([obj, klass])
    assert isinstance(isinst, cst.Assert)
    assert isinstance(isinst.test, cst.Call)

    notisinst = assertions._assert_not_is_instance([obj, klass])
    assert isinstance(notisinst, cst.Assert)
    assert isinstance(notisinst.test, cst.UnaryOperation)


def test_comparisons():
    a = _a("5")
    b = _a("3")
    greater = assertions._assert_greater([a, b])
    assert isinstance(greater, cst.Assert)
    assert isinstance(greater.test, cst.Comparison)

    ge = assertions._assert_greater_equal([a, b])
    assert isinstance(ge, cst.Assert)

    less = assertions._assert_less([b, a])
    assert isinstance(less, cst.Assert)

    le = assertions._assert_less_equal([b, a])
    assert isinstance(le, cst.Assert)
