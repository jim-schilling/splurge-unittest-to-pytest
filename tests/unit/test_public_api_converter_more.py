import libcst as cst

from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer


def test_pattern_adders_and_props() -> None:
    t = UnittestToPytestTransformer()

    # default patterns contain typical values
    assert any(p.lower().startswith("test") for p in t.test_patterns)

    # add custom patterns and verify they're present
    t.add_setup_pattern("setup_class")
    assert any("setup_class" == p or "setup_class" in p for p in t.setup_patterns)

    t.add_teardown_pattern("teardown_class")
    assert any("teardown_class" == p or "teardown_class" in p for p in t.teardown_patterns)

    t.add_test_pattern("describe_")
    assert any(p.startswith("describe_") for p in t.test_patterns)


def test_assert_raises_helpers_and_import_flag() -> None:
    t = UnittestToPytestTransformer()

    # Initially, transformer should not require pytest import
    assert not t.needs_pytest_import

    # Build a fake assertRaises call args (Exception, func)
    exc = cst.Name("Exception")
    # create a dummy call arg list; actual structure isn't deeply inspected here
    args = (cst.Arg(value=exc),)

    call_node = t._assert_raises(args)
    # Using the helper should set the flag and return a Call node
    assert t.needs_pytest_import
    assert isinstance(call_node, cst.Call)

    # Reset flag and test assertRaisesRegex helper
    t.needs_pytest_import = False
    regex_call = t._assert_raises_regex(args)
    assert t.needs_pytest_import
    assert isinstance(regex_call, cst.Call)


def test_add_pytest_import_wrapper_returns_module_with_import() -> None:
    t = UnittestToPytestTransformer()
    module = cst.parse_module("\n")
    new_module = t._add_pytest_import(module)

    # The returned module code should contain 'import pytest' somewhere
    assert "pytest" in new_module.code


def test_fixture_creation_delegation_simple_and_attribute() -> None:
    t = UnittestToPytestTransformer()

    # Create a simple literal expression and ensure a fixture function is created
    expr = cst.parse_expression("1")
    fx = t._create_simple_fixture("my_attr", expr)
    assert isinstance(fx, cst.FunctionDef)
    assert fx.name.value == "my_attr"

    # Creating fixture for attribute should return a FunctionDef as well
    fx2 = t._create_fixture_for_attribute("other", expr)
    assert isinstance(fx2, cst.FunctionDef)


def test_remove_self_references_simple_attribute():
    t = UnittestToPytestTransformer(compat=False)
    node = cst.parse_expression("self.value")
    new_node = t._remove_self_references(node)
    # result should be the attribute name only (Name 'value')
    from libcst import Name

    assert isinstance(new_node, Name)
    assert new_node.value == "value"


def test_convert_assertion_name_fallback_to_converter():
    t = UnittestToPytestTransformer(compat=False)
    call_node = cst.parse_expression("assertEqual(1, 2)")
    res = t._convert_self_assertion_to_pytest(call_node)
    assert res is not None
    # render the Assert into code by placing it in a simple module line
    module = cst.Module(body=[cst.SimpleStatementLine([res])])
    assert "1 == 2" in module.code


def test_create_pytest_raises_item_sets_import_flag():
    t = UnittestToPytestTransformer(compat=False)
    call_node = cst.parse_expression("self.assertRaises(ValueError, func, arg)")
    # extract args from parsed call
    args = call_node.args
    item = t._create_pytest_raises_item("assertRaises", args)
    assert hasattr(item, "item")
    # render the Call into code by wrapping in an Expr inside a Module
    rendered = cst.Module(body=[cst.SimpleStatementLine([cst.Expr(item.item)])]).code
    assert "pytest.raises" in rendered
    assert t.needs_pytest_import is True


def test_convert_setup_to_fixture_creates_assignments_and_fixtures():
    t = UnittestToPytestTransformer(compat=False)
    func = cst.parse_statement("def setUp(self):\n    self.x = 1\n")
    # call internal converter that should record assignments and create fixtures
    result = t._convert_setup_to_fixture(func)
    from libcst import RemovalSentinel

    assert result is RemovalSentinel.REMOVE
    # assignments and fixtures should be populated for attribute 'x'
    assert "x" in t.setup_assignments
    assert "x" in t.setup_fixtures


def test_visit_classdef_removes_unittest_base():
    src = "import unittest\n\nclass TestExample(unittest.TestCase):\n    pass\n"
    mod = cst.parse_module(src)
    t = UnittestToPytestTransformer(compat=False)
    new_mod = mod.visit(t)
    # the transformed module should no longer contain 'unittest.TestCase' base
    assert "unittest.TestCase" not in new_mod.code
