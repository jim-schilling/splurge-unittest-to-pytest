import libcst as cst

from splurge_unittest_to_pytest.main import PatternConfigurator, convert_string
from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def test_transformer_pattern_adders_and_checks():
    pc = PatternConfigurator()
    pc.add_setup_pattern("before_all")
    assert "before_all" in pc.setup_patterns
    pc.add_teardown_pattern("after_all")
    assert "after_all" in pc.teardown_patterns
    pc.add_test_pattern("describe_")
    assert "describe_" in pc.test_patterns
    assert pc._is_setup_method("setUp") is True
    assert pc._is_teardown_method("tearDown") is True
    assert pc._is_test_method("test_something") is True


def test_is_self_call_and_pytest_import_add_and_add_pytest_import():
    src = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    res = convert_string(src)
    assert "pytest.raises" in res.converted_code
    assert "import pytest" in res.converted_code or "pytest" in res.converted_code


def test_assertion_rewriter_with_and_regex_conversions():
    src_with = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    mod = cst.parse_module(src_with)
    out = assertion_rewriter_stage({"module": mod})
    new_mod = out["module"]
    assert "pytest.raises" in new_mod.code
    assert out.get("needs_pytest_import", False) is True
    src_regex = "def test():\n    self.assertRegex(text, pattern)\n"
    mod2 = cst.parse_module(src_regex)
    out2 = assertion_rewriter_stage({"module": mod2})
    new_mod2 = out2["module"]
    assert "re.search" in new_mod2.code
    assert out2.get("needs_re_import", False) is True
