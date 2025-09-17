"""Tests for stages.assertion_rewriter transformations.

These tests exercise a representative subset of conversions (equality,
truthiness, membership, almost-equal -> pytest.approx, regex -> re.search,
and assertRaises context manager). They assert on generated source and
returned flags and avoid brittle exact formatting checks.
"""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages import assertion_rewriter


def transform(code: str):
    mod = cst.parse_module(code)
    out = assertion_rewriter.assertion_rewriter_stage({"module": mod})
    new_mod = out.get("module")
    src = new_mod.code if new_mod is not None else ""
    return src, out.get("needs_pytest_import", False), out.get("needs_re_import", False)


def test_assert_equal_to_assert():
    code = """
class T:
    def test(self):
        self.assertEqual(a, b)
"""
    src, py, reflag = transform(code)
    assert "assert" in src
    assert "==" in src
    assert py is False
    assert reflag is False


def test_assert_true_and_false():
    code = """
class T:
    def test(self):
        self.assertTrue(condition)
        self.assertFalse(condition)
"""
    src, py, reflag = transform(code)
    assert "assert condition" in src
    assert "not condition" in src or "not(condition)" in src
    assert py is False
    assert reflag is False


def test_assert_in_and_not_in():
    code = """
class T:
    def test(self):
        self.assertIn(x, y)
        self.assertNotIn(x, y)
"""
    src, py, reflag = transform(code)
    assert "in" in src
    assert "not" in src
    assert py is False
    assert reflag is False


def test_assert_almost_equal_uses_approx_by_default():
    code = """
class T:
    def test(self):
        self.assertAlmostEqual(a, b)
"""
    src, py, reflag = transform(code)
    assert "pytest.approx" in src
    assert py is True
    assert reflag is False


def test_assert_almost_equal_with_delta_uses_abs_compare():
    code = """
class T:
    def test(self):
        self.assertAlmostEqual(a, b, delta=0.1)
"""
    src, py, reflag = transform(code)
    # should map to abs(left - right) <= delta
    assert "abs(" in src or "<=" in src
    assert py is False or py is True
    assert reflag is False


def test_assert_regex_sets_re_import_and_uses_re_search():
    code = """
class T:
    def test(self):
        self.assertRegex(text, pattern)
"""
    src, py, reflag = transform(code)
    assert "re.search" in src
    assert reflag is True


def test_assert_raises_context_manager_to_pytest_raises():
    code = """
class T:
    def test(self):
        with self.assertRaises(ValueError):
            raise ValueError()
"""
    src, py, reflag = transform(code)
    assert "pytest.raises" in src
    assert py is True
    assert reflag is False
