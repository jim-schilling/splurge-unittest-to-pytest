import libcst as cst

from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer
from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def test_transformer_pattern_adders_and_checks():
    t = UnittestToPytestTransformer(compat=False)

    # add setup/teardown/test patterns and verify they're present
    t.add_setup_pattern("before_all")
    assert "before_all" in t.setup_patterns

    t.add_teardown_pattern("after_all")
    assert "after_all" in t.teardown_patterns

    t.add_test_pattern("describe_")
    assert "describe_" in t.test_patterns

    # basic method classification
    assert t._is_setup_method("setUp") is True
    assert t._is_teardown_method("tearDown") is True
    assert t._is_test_method("test_something") is True


def test_is_self_call_and_pytest_import_add_and_add_pytest_import():
    t = UnittestToPytestTransformer(compat=False)

    # craft a self.assertRaises(...) call
    call_node = cst.parse_expression("self.assertRaises(ValueError, func, arg)")
    info = t._is_self_call(call_node)
    assert info is not None
    method_name, args = info
    assert method_name == "assertRaises"

    # _assert_raises should set needs_pytest_import and return a pytest.raises Call
    result_call = t._assert_raises(args)
    assert t.needs_pytest_import is True
    # result_call.func should be an Attribute with value Name 'pytest' and attr 'raises'
    assert isinstance(result_call.func, cst.Attribute)
    assert isinstance(result_call.func.value, cst.Name)
    assert result_call.func.value.value == "pytest"
    assert result_call.func.attr.value == "raises"

    # _add_pytest_import should inject import into module
    mod = cst.parse_module("x = 1")
    new_mod = t._add_pytest_import(mod)
    assert "import pytest" in new_mod.code


def test_assertion_rewriter_with_and_regex_conversions():
    # with self.assertRaises -> with pytest.raises
    src_with = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    mod = cst.parse_module(src_with)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "pytest.raises" in new_mod.code
    assert out.get("needs_pytest_import", False) is True

    # assertRegex -> re.search and sets needs_re_import
    src_regex = "def test():\n    self.assertRegex(text, pattern)\n"
    mod2 = cst.parse_module(src_regex)
    out2 = assertion_rewriter_stage({"module": mod2})
    new_mod2 = out2["module"]
    assert "re.search" in new_mod2.code
    assert out2.get("needs_re_import", False) is True
