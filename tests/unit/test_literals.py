from libcst import parse_expression
from splurge_unittest_to_pytest.stages.generator_parts.literals import is_literal


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
    # names are not considered literals
    assert not is_literal(parse_expression("foo"))
    # calls are not literals
    assert not is_literal(parse_expression("open('x')"))
