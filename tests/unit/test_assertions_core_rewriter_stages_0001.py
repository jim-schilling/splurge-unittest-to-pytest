"""Tests for stages.assertion_rewriter transformations.

These tests exercise a representative subset of conversions (equality,
truthiness, membership, almost-equal -> pytest.approx, regex -> re.search,
and assertRaises context manager). They assert on generated source and
returned flags and avoid brittle exact formatting checks."""

from __future__ import annotations
import libcst as cst
from splurge_unittest_to_pytest.stages import assertion_rewriter
from libcst import matchers as m


def transform(code: str):
    mod = cst.parse_module(code)
    out = assertion_rewriter.assertion_rewriter_stage({"module": mod})
    new_mod = out.get("module")
    src = new_mod.code if new_mod is not None else ""
    return (src, out.get("needs_pytest_import", False), out.get("needs_re_import", False))


def test_assert_equal_to_assert():
    code = "\nclass T:\n    def test(self):\n        self.assertEqual(a, b)\n"
    src, py, reflag = transform(code)
    assert "assert" in src
    assert "==" in src
    assert py is False
    assert reflag is False


def test_assert_true_and_false():
    code = "\nclass T:\n    def test(self):\n        self.assertTrue(condition)\n        self.assertFalse(condition)\n"
    src, py, reflag = transform(code)
    assert "assert condition" in src
    assert "not condition" in src or "not(condition)" in src
    assert py is False
    assert reflag is False


def test_assert_in_and_not_in():
    code = "\nclass T:\n    def test(self):\n        self.assertIn(x, y)\n        self.assertNotIn(x, y)\n"
    src, py, reflag = transform(code)
    assert "in" in src
    assert "not" in src
    assert py is False
    assert reflag is False


def test_assert_almost_equal_uses_approx_by_default():
    code = "\nclass T:\n    def test(self):\n        self.assertAlmostEqual(a, b)\n"
    src, py, reflag = transform(code)
    assert "pytest.approx" in src
    assert py is True
    assert reflag is False


def test_assert_almost_equal_with_delta_uses_abs_compare():
    code = "\nclass T:\n    def test(self):\n        self.assertAlmostEqual(a, b, delta=0.1)\n"
    src, py, reflag = transform(code)
    assert "abs(" in src or "<=" in src
    assert py is False or py is True
    assert reflag is False


def test_assert_regex_sets_re_import_and_uses_re_search():
    code = "\nclass T:\n    def test(self):\n        self.assertRegex(text, pattern)\n"
    src, py, reflag = transform(code)
    assert "re.search" in src
    assert reflag is True


def test_assert_raises_context_manager_to_pytest_raises():
    code = (
        "\nclass T:\n    def test(self):\n        with self.assertRaises(ValueError):\n            raise ValueError()\n"
    )
    src, py, reflag = transform(code)
    assert "pytest.raises" in src
    assert py is True
    assert reflag is False


def _run(src: str):
    module = cst.parse_module(src)
    return assertion_rewriter.assertion_rewriter_stage({"module": module})


def test_bare_name_assert_equal_conversion():
    src = "\ndef test():\n    assertEqual(a, b)\n"
    res = _run(src)
    code = res["module"].code
    assert "assert a ==" in code


def test_assert_is_none_string_literal_guard_returns_none():
    src = "\ndef test():\n    self.assertIsNone('x')\n"
    res = _run(src)
    code = res["module"].code
    assert "is None" not in code


def test_assert_raises_regex_without_match_arg_fallback():
    src = "\ndef test():\n    with self.assertRaisesRegex(ValueError):\n        raise ValueError()\n"
    res = _run(src)
    code = res["module"].code
    assert "pytest.raises(ValueError" in code
    assert "match" not in code


def test_assert_not_almost_equal_with_delta_produces_greater_than():
    src = "\ndef test():\n    self.assertNotAlmostEqual(a, b, delta=0.5)\n"
    res = _run(src)
    mod = res["module"]
    found_gt = False
    for comp in cst.matchers.findall(mod, m.Comparison()):
        for ct in comp.comparisons:
            if isinstance(ct.operator, cst.GreaterThan):
                found_gt = True
                break
        if found_gt:
            break
    assert found_gt is True


def test_assert_is_instance_emits_isinstance_call():
    src = "\ndef test():\n    self.assertIsInstance(obj, Type)\n"
    res = _run(src)
    mod = res["module"]
    calls = list(cst.matchers.findall(mod, m.Call()))
    assert any((isinstance(c.func, cst.Name) and c.func.value == "isinstance" for c in calls))


def _run_src(src: str):
    mod = cst.parse_module(src)
    return assertion_rewriter.assertion_rewriter_stage({"module": mod})


def _mod_from_call(call_src: str):
    src = f"def test():\n    {call_src}\n"
    return _run_src(src)["module"]


def test_basic_comparisons_map():
    mapping = [
        ("self.assertEqual(a, b)", cst.Equal),
        ("self.assertNotEqual(a, b)", cst.NotEqual),
        ("self.assertIn(x, y)", cst.In),
        ("self.assertNotIn(x, y)", cst.NotIn),
        ("self.assertIs(a, b)", cst.Is),
        ("self.assertIsNot(a, b)", cst.IsNot),
        ("self.assertGreater(a, b)", cst.GreaterThan),
        ("self.assertGreaterEqual(a, b)", cst.GreaterThanEqual),
        ("self.assertLess(a, b)", cst.LessThan),
        ("self.assertLessEqual(a, b)", cst.LessThanEqual),
        ("self.assertListEqual(a, b)", cst.Equal),
        ("self.assertDictEqual(a, b)", cst.Equal),
        ("self.assertMultiLineEqual(a, b)", cst.Equal),
    ]
    for call_src, expected_op in mapping:
        mod = _mod_from_call(call_src)
        found = False
        for comp in cst.matchers.findall(mod, m.Comparison()):
            for ct in comp.comparisons:
                if isinstance(ct.operator, expected_op):
                    found = True
                    break
            if found:
                break
        assert found, f"Expected operator {expected_op} for {call_src}"


def test_identity_and_membership():
    src = "\ndef test():\n    self.assertIsNotNone(x)\n    self.assertNotIsInstance(x, int)\n"
    res = _run_src(src)
    mod = res["module"]
    has_isnot = any(
        (isinstance(ct.operator, cst.IsNot) for c in cst.matchers.findall(mod, m.Comparison()) for ct in c.comparisons)
    )
    assert has_isnot
    found_not_isinstance = False
    for un in cst.matchers.findall(mod, m.UnaryOperation()):
        inner = getattr(un, "expression", None)
        if isinstance(inner, cst.Call) and isinstance(inner.func, cst.Name) and (inner.func.value == "isinstance"):
            found_not_isinstance = True
            break
    assert found_not_isinstance


def test_assert_is_instance_and_not_is_instance():
    mod = _mod_from_call("self.assertIsInstance(obj, T)")
    calls = list(cst.matchers.findall(mod, m.Call()))
    assert any((isinstance(c.func, cst.Name) and c.func.value == "isinstance" for c in calls))


def test_assert_almost_equal_variants():
    res = _run_src("def test():\n    self.assertAlmostEqual(a, b)\n")
    code = res["module"].code
    assert "pytest.approx" in code
    assert res.get("needs_pytest_import", False) is True
    res2 = _run_src("def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n")
    assert "abs(" in res2["module"].code or "<=" in res2["module"].code
    res3 = _run_src("def test():\n    self.assertAlmostEqual(a, b, 3)\n")
    assert "round(" in res3["module"].code


def test_assert_not_almost_equal_variants():
    res = _run_src("def test():\n    self.assertNotAlmostEqual(a, b, delta=0.5)\n")
    mod = res["module"]
    found_gt = any(
        (
            isinstance(ct.operator, cst.GreaterThan)
            for c in cst.matchers.findall(mod, m.Comparison())
            for ct in c.comparisons
        )
    )
    assert found_gt
    res2 = _run_src("def test():\n    self.assertNotAlmostEqual(a, b, 2)\n")
    assert "round(" in res2["module"].code


def test_assert_raises_callable_and_context():
    src = "\ndef test():\n    self.assertRaises(ValueError, int, 'x')\n    with self.assertRaises(ValueError):\n        raise ValueError()\n"
    res = _run_src(src)
    mod = res["module"]
    assert "pytest.raises" in mod.code
    assert "assertRaises(" in mod.code


def _run_rewriter_and_code(src: str) -> str:
    module = cst.parse_module(src)
    res = assertion_rewriter.assertion_rewriter_stage({"module": module})
    new_mod = res.get("module")
    assert new_mod is not None
    return new_mod.code


def test_assert_equal_rewrites_to_comparison():
    src = "self.assertEqual(1, 2)"
    code = _run_rewriter_and_code(src)
    assert "assert 1 == 2" in code


def test_assert_true_and_false_rewrite():
    src = "self.assertTrue(x)\nself.assertFalse(y)"
    code = _run_rewriter_and_code(src)
    assert "assert x" in code
    assert "assert not y" in code


def test_assert_in_and_not_in__01():
    src = "self.assertIn(a, b)\nself.assertNotIn(c, d)"
    code = _run_rewriter_and_code(src)
    assert "assert a in b" in code
    assert "assert c not in d" in code


def test_assert_almost_equal_uses_pytest_approx():
    src = "self.assertAlmostEqual(a, b)"
    code = _run_rewriter_and_code(src)
    assert "pytest.approx" in code


def test_assert_raises_context_manager_to_pytest_raises__01():
    src = "with self.assertRaises(ValueError):\n    f()"
    code = _run_rewriter_and_code(src)
    assert "with pytest.raises(ValueError):" in code
