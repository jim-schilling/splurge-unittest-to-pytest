import libcst as cst
from libcst import parse_expression

from splurge_unittest_to_pytest.stages.generator_parts import literals
from splurge_unittest_to_pytest.stages.generator_parts.literals import is_literal


def test_is_literal_none_and_name():
    assert literals.is_literal(None) is False
    assert literals.is_literal(cst.Name("x")) is False


def test_is_literal_numbers_and_strings_and_containers():
    assert literals.is_literal(cst.Integer("123")) is True
    assert literals.is_literal(cst.Float("1.2")) is True
    assert literals.is_literal(cst.SimpleString('"ok"')) is True
    assert literals.is_literal(cst.Tuple(elements=[cst.Element(cst.Integer("1"))])) is True
    assert literals.is_literal(cst.List(elements=[cst.Element(cst.SimpleString('"a"'))])) is True
    assert literals.is_literal(cst.Set(elements=[cst.Element(cst.Integer("2"))])) is True
    assert literals.is_literal(cst.Dict(elements=[cst.DictElement(cst.SimpleString('"k"'), cst.Integer("1"))])) is True


def test_literals_simple():
    assert is_literal(parse_expression("42"))
    assert is_literal(parse_expression("3.14"))
    assert is_literal(parse_expression("'x'"))


def test_literals_containers():
    assert is_literal(parse_expression("[1, 2, 3]"))
    assert is_literal(parse_expression("(1, 'a')"))
    assert is_literal(parse_expression("{'a': 1}"))
    assert is_literal(parse_expression("{1,2,3}"))


def test_non_literals():
    assert not is_literal(parse_expression("foo"))
    assert not is_literal(parse_expression("open('x')"))
