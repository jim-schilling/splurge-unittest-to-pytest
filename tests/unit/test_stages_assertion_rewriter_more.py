import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def run_stage(src: str):
    mod = cst.parse_module(src)
    out = assertion_rewriter_stage({"module": mod})
    return out["module"], out.get("needs_pytest_import", False), out.get("needs_re_import", False)


def test_trailing_msg_is_removed_from_assert_equal():
    src = "def test():\n    self.assertEqual(a, b, 'message')\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "a == b" in code
    assert "message" not in code


def test_assert_is_none_literal_guard_and_expr():
    # literal path should be left unchanged
    src_lit = "def test():\n    self.assertIsNone(1)\n"
    mod_lit, _, _ = run_stage(src_lit)
    assert "self.assertIsNone(1)" in mod_lit.code

    # expression path should convert to 'is None'
    src_expr = "def test():\n    self.assertIsNone(x)\n"
    mod_expr, _, _ = run_stage(src_expr)
    assert "x is None" in mod_expr.code


def test_assert_is_and_is_not():
    src = "def test():\n    self.assertIs(a, b)\n    self.assertIsNot(a, b)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "a is b" in code
    assert "a is not b" in code


def test_assert_isinstance_and_not_isinstance():
    src = "def test():\n    self.assertIsInstance(obj, Type)\n    self.assertNotIsInstance(obj, Type)\n"
    mod, _, _ = run_stage(src)
    code = mod.code
    assert "isinstance" in code
    assert "not isinstance" in code or "not(" in code


def test_assert_almost_equal_default_uses_approx_and_requires_pytest():
    src = "def test():\n    self.assertAlmostEqual(a, b)\n"
    mod, needs_pytest, _ = run_stage(src)
    code = mod.code
    assert "pytest.approx" in code
    assert needs_pytest is True


def test_assert_not_regex_sets_re_import_and_not_search():
    src = "def test():\n    self.assertNotRegex(text, pattern)\n"
    mod, _, needs_re = run_stage(src)
    code = mod.code
    assert "re.search" in code
    assert needs_re is True
    assert "not" in code
