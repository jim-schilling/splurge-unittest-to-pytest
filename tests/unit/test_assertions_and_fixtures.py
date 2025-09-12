import libcst as cst

from splurge_unittest_to_pytest.converter.assertion_dispatch import convert_assertion
from splurge_unittest_to_pytest.converter.assertions import _assert_equal, _assert_is_none
from splurge_unittest_to_pytest.converter.fixtures import create_simple_fixture, add_autouse_attach_fixture_to_module


def _arg_from_expr(src: str) -> cst.Arg:
    expr = cst.parse_expression(src)
    return cst.Arg(value=expr)


def test_assert_equal_direct_helper():
    a1 = _arg_from_expr("1")
    a2 = _arg_from_expr("2")
    node = _assert_equal([a1, a2])
    assert isinstance(node, cst.Assert)
    # verify the Assert contains a Comparison with Equal operator and comparator 2
    assert isinstance(node.test, cst.Comparison)
    comps = node.test.comparisons
    assert len(comps) == 1
    assert isinstance(comps[0].operator, cst.Equal)
    # comparator should be the integer literal 2
    assert isinstance(comps[0].comparator, cst.Integer)


def test_convert_assertion_via_map():
    a1 = _arg_from_expr("x")
    a2 = _arg_from_expr("y")
    res = convert_assertion("assertEqual", [a1, a2])
    assert isinstance(res, cst.Assert)


def test_assert_is_none_returns_none_for_literals():
    a1 = _arg_from_expr("1")
    node = _assert_is_none([a1])
    # For literal integer argument, _assert_is_none returns None to avoid `1 is None`
    assert node is None


def test_create_simple_fixture_and_autouse_attach_insertion():
    # create a simple fixture function
    val_expr = cst.parse_expression("42")
    fixture = create_simple_fixture("my_fixture", val_expr)
    assert isinstance(fixture, cst.FunctionDef)
    # create a module and insert autouse attach fixture
    module = cst.parse_module("\n")
    mod2 = add_autouse_attach_fixture_to_module(module, {"my_fixture": fixture})
    # ensure the _attach_to_instance function name appears among module function defs
    found = any(isinstance(s, cst.FunctionDef) and s.name.value == "_attach_to_instance" for s in mod2.body)
    assert found
