import libcst as cst
from splurge_unittest_to_pytest.converter import assertions


def make_arg(value_expr: cst.BaseExpression) -> cst.Arg:
    return cst.Arg(value=value_expr)


def test_assert_equal_and_not_equal():
    a = make_arg(cst.Name("x"))
    b = make_arg(cst.Name("y"))
    node = assertions._assert_equal([a, b])
    assert isinstance(node, cst.Assert)
    # comparison should use Equal operator
    assert isinstance(node.test, cst.Comparison)

    node2 = assertions._assert_not_equal([a, b])
    assert isinstance(node2, cst.Assert)
    assert isinstance(node2.test, cst.Comparison)


def test_assert_true_false():
    a = make_arg(cst.Name("cond"))
    n1 = assertions._assert_true([a])
    assert isinstance(n1, cst.Assert)
    n2 = assertions._assert_false([a])
    assert isinstance(n2, cst.Assert)
    # false should wrap expression in UnaryOperation Not
    assert isinstance(n2.test, cst.UnaryOperation)


def test_assert_is_none_and_not_none():
    # for literal should return None
    lit = make_arg(cst.Integer("1"))
    assert assertions._assert_is_none([lit]) is None

    # for name should return comparison is None
    n = make_arg(cst.Name("maybe"))
    node = assertions._assert_is_none([n])
    assert isinstance(node, cst.Assert)
    node2 = assertions._assert_is_not_none([n])
    assert isinstance(node2, cst.Assert)


def test_assert_in_notin_instance_and_comparisons():
    a = make_arg(cst.Name("a"))
    b = make_arg(cst.Name("b"))
    assert isinstance(assertions._assert_in([a, b]), cst.Assert)
    assert isinstance(assertions._assert_not_in([a, b]), cst.Assert)
    # isinstance
    assert isinstance(assertions._assert_is_instance([a, b]), cst.Assert)
    assert isinstance(assertions._assert_not_is_instance([a, b]), cst.Assert)
    # greater/less
    assert isinstance(assertions._assert_greater([a, b]), cst.Assert)
    assert isinstance(assertions._assert_greater_equal([a, b]), cst.Assert)
    assert isinstance(assertions._assert_less([a, b]), cst.Assert)
    assert isinstance(assertions._assert_less_equal([a, b]), cst.Assert)
