"""Tests for stages.raises_stage transformers.

These tests exercise the public behavior of ExceptionAttrRewriter and
RaisesRewriter using LibCST to parse and transform small snippets. They
avoid brittle exact formatting assertions and instead check for
presence/absence of key substrings and transformer state changes.
"""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def transform_code(code: str, transformer: cst.CSTTransformer) -> str:
    mod = cst.parse_module(code)
    new = mod.visit(transformer)
    # LibCST Module exposes a .code property that returns the generated
    # Python source for the transformed tree.
    try:
        return new.code
    except Exception:
        return str(new)


def test_exception_attr_rewriter_rewrites_simple_attribute():
    code = """
def f():
    cm = None
    x = cm.exception
"""
    tr = raises_stage.ExceptionAttrRewriter("cm")
    out = transform_code(code, tr)

    assert "cm.value" in out
    assert "cm.exception" not in out


def test_exception_attr_rewriter_respects_shadowing_in_function():
    code = """
def f(cm):
    x = cm.exception
"""
    tr = raises_stage.ExceptionAttrRewriter("cm")
    out = transform_code(code, tr)

    # parameter shadows outer name -> should not rewrite
    assert "cm.exception" in out
    assert "cm.value" not in out


def test_exception_attr_rewriter_respects_lambda_shadowing():
    code = """
def outer():
    cm = None
    f = lambda cm: cm.exception
    return f
"""
    tr = raises_stage.ExceptionAttrRewriter("cm")
    out = transform_code(code, tr)

    # lambda parameter shadows the outer 'cm', so usage inside lambda stays
    assert "cm.exception" in out


def test_raises_rewriter_context_manager_and_attribute_rewrite():
    code = """
import unittest

class T(unittest.TestCase):
    def test_it(self):
        with self.assertRaises(ValueError) as cm:
            raise ValueError()
        x = cm.exception
"""
    tr = raises_stage.RaisesRewriter()
    out = transform_code(code, tr)

    # should have converted to pytest.raises and rewritten attribute access
    assert "pytest.raises" in out
    assert "cm.value" in out
    assert "cm.exception" not in out
    assert tr.made_changes is True


def test_raises_rewriter_functional_form_transforms_to_with():
    code = """
import unittest

class T(unittest.TestCase):
    def test_it(self):
        self.assertRaises(ValueError, some_func, 1, 2)
"""
    tr = raises_stage.RaisesRewriter()
    out = transform_code(code, tr)

    # functional form should be converted into a with pytest.raises and call
    assert "pytest.raises" in out
    assert "some_func(" in out
    assert tr.made_changes is True


def test_raises_rewriter_regex_uses_match_keyword():
    code = """
import unittest

class T(unittest.TestCase):
    def test_it(self):
        with self.assertRaisesRegex(ValueError, "bad") as cm:
            raise ValueError("bad")
        x = cm.exception
"""
    tr = raises_stage.RaisesRewriter()
    out = transform_code(code, tr)

    # should have pytest.raises with match keyword and attribute rewritten
    assert "pytest.raises" in out
    # codegen may insert spaces around '=', so just check for the keyword
    assert "match" in out
    assert "cm.value" in out
