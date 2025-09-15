import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage

DOMAINS = ["assertions", "rewriter", "stages"]


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False)


def test_assert_true_and_false_paths():
    src = "def test():\n    self.assertTrue(cond)\n    self.assertFalse(cond2)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "cond" in code
    assert "not cond2" in code


def test_assert_is_not_none_and_comparisons():
    src = "def test():\n    self.assertIsNotNone(x)\n    self.assertGreater(a, b)\n    self.assertLess(c, d)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "x is not None" in code
    assert "a > b" in code
    assert "c < d" in code


def test_assert_not_equal_maps_to_not_equal():
    src = "def test():\n    self.assertNotEqual(p, q)\n"
    mod, _, _ = run_stage(src)
    assert "p != q" in mod.code
