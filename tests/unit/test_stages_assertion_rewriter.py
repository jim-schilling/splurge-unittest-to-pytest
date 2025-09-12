import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False)


def test_assert_equal_to_comparison():
    src = "def test():\n    self.assertEqual(a, b)\n"
    mod, needs_pytest, needs_re = run_stage(src)
    code = mod.code
    assert "a == b" in code
    assert needs_pytest is False
    assert needs_re is False


def test_assert_false_to_not():
    src = "def test():\n    self.assertFalse(x)\n"
    mod, _, _ = run_stage(src)
    assert "not x" in mod.code


def test_assert_almost_equal_with_delta_uses_abs_le():
    src = "def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "abs(" in code and "<=" in code
    # delta path should not require pytest approx
    assert needs_pytest is False


def test_assert_almost_equal_with_places_positional_uses_round():
    src = "def test():\n    self.assertAlmostEqual(a, b, 3)\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "round(" in code and "== 0" in code
    assert needs_pytest is False


def test_assert_not_almost_equal_with_delta_uses_gt():
    src = "def test():\n    self.assertNotAlmostEqual(a, b, delta=0.2)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "abs(" in code and ">" in code


def test_assert_regex_sets_re_import_and_search():
    src = "def test():\n    self.assertRegex(text, pattern)\n"
    mod, _, needs_re = run_stage(src)
    code = mod.code
    assert "re.search" in code
    assert needs_re is True


def test_assert_raises_context_manager_to_pytest_raises():
    src = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "pytest.raises(ValueError)" in code
    assert needs_pytest is True


def test_assert_in_and_not_in():
    src = "def test():\n    self.assertIn(x, coll)\n    self.assertNotIn(x, coll)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "in coll" in code
    assert "not in coll" in code
