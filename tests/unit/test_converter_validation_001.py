import libcst as cst

from splurge_unittest_to_pytest.converter.value_checks import is_simple_fixture_value

DOMAINS = ["converter", "validation"]


def test_is_simple_fixture_value_true_for_literals():
    assert is_simple_fixture_value(cst.Integer("42"))
    assert is_simple_fixture_value(cst.Float("1.5"))
    assert is_simple_fixture_value(cst.SimpleString("'a'"))


def test_is_simple_fixture_value_false_for_complex():
    assert not is_simple_fixture_value(cst.Name("foo"))
    assert not is_simple_fixture_value(cst.Call(func=cst.Name("make"), args=[]))
