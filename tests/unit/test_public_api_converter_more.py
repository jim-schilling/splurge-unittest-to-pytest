import libcst as cst

from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer


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
