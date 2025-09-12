import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def _out_code(src: str) -> tuple[str, dict]:
    mod = cst.parse_module(src)
    res = assertion_rewriter_stage({"module": mod})
    return res["module"].code, res


def test_is_and_is_not_conversions():
    code, _ = _out_code("""
def test():
    self.assertIs(a, b)
    self.assertIsNot(a, b)
""")
    assert "is b" in code
    assert "is not b" in code


def test_in_and_not_in_and_collection_equal():
    code, _ = _out_code("""
def test():
    self.assertIn(x, y)
    self.assertNotIn(x, y)
    self.assertListEqual(a, b)
""")
    assert "in y" in code
    assert "not in" in code
    assert "== b" in code


def test_isinstance_and_not_isinstance():
    code, _ = _out_code("""
def test():
    self.assertIsInstance(x, T)
    self.assertNotIsInstance(x, T)
""")
    assert "isinstance(x, T)" in code
    assert "not isinstance" in code


def test_comparison_variants():
    code, _ = _out_code("""
def test():
    self.assertGreater(a, b)
    self.assertGreaterEqual(a, b)
    self.assertLess(a, b)
    self.assertLessEqual(a, b)
""")
    assert ">" in code
    assert ">=" in code or ">=" in code
    assert "<" in code
    assert "<=" in code or "<=" in code


def test_almost_equal_with_numeric_third_positional_keeps_places():
    code, _ = _out_code("""
def test():
    self.assertAlmostEqual(a, b, 3)
""")
    # round(..., 3) == 0 expected
    assert "round" in code and ", 3" in code


def test_multi_line_and_regex_variants_present():
    code, res = _out_code("""
def test():
    self.assertMultiLineEqual(s1, s2)
    self.assertRegex(s, pat)
    self.assertNotRegex(s, pat)
""")
    assert "== s2" in code or "== s2" in code
    assert "re.search" in code
    assert res.get("needs_re_import") is True
