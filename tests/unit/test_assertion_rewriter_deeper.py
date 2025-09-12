import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def _mod(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_assert_regex_sets_re_import_and_search_expression():
    src = """
def test_it():
    self.assertRegex(text, pattern)
"""
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "re.search" in new.code
    assert out.get("needs_re_import") is True


def test_assert_not_regex_negates_search_and_sets_re_import():
    src = """
def test_it():
    self.assertNotRegex(text, pattern)
"""
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "not re.search" in new.code
    assert out.get("needs_re_import") is True


def test_assert_is_none_literal_guard_returns_none_behavior():
    src = """
def test_it():
    self.assertIsNone(1)
"""
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    # should not produce 'is None' for numeric literal
    assert "is None" not in new.code


def test_assert_almost_equal_with_delta_uses_abs_compare():
    src = """
def test_it():
    self.assertAlmostEqual(a, b, delta=0.1)
"""
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    assert "abs" in new.code and "<=" in new.code


def test_assert_not_almost_equal_default_uses_not_approx():
    src = """
def test_it():
    self.assertNotAlmostEqual(a, b)
"""
    out = assertion_rewriter_stage({"module": _mod(src)})
    new = out["module"]
    # not equal to pytest.approx form
    assert "pytest.approx" in new.code
