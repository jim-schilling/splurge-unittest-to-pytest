from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter.assertions import ASSERTIONS_MAP


def _render_assert(assert_node: cst.Assert) -> str:
    # Wrap the assert node in a module so libcst can render it to source
    mod = cst.Module(body=[cst.SimpleStatementLine(body=[assert_node])])
    return mod.code.strip()


def _arg(name: str) -> cst.Arg:
    return cst.Arg(value=cst.Name(name))


def test_assert_equal_handler_renders_comparison() -> None:
    handler = ASSERTIONS_MAP["assertEqual"]
    node = handler([_arg("a"), _arg("b")])
    assert isinstance(node, cst.Assert)
    assert _render_assert(node) == "assert a == b"


def test_assert_is_none_literal_returns_none_and_variable_renders() -> None:
    handler = ASSERTIONS_MAP["assertIsNone"]
    # literal should return None to avoid `assert 1 is None`
    lit = handler([cst.Arg(value=cst.Integer(value="1"))])
    assert lit is None

    # variable should produce `assert x is None`
    var = handler([_arg("x")])
    assert isinstance(var, cst.Assert)
    assert _render_assert(var) == "assert x is None"


def test_assert_true_false_and_in_isinstance() -> None:
    t_true = ASSERTIONS_MAP["assertTrue"]([_arg("cond")])
    assert _render_assert(t_true) == "assert cond"

    t_false = ASSERTIONS_MAP["assertFalse"]([_arg("cond")])
    assert _render_assert(t_false) == "assert not cond"

    t_in = ASSERTIONS_MAP["assertIn"]([_arg("a"), _arg("b")])
    assert _render_assert(t_in) == "assert a in b"

    t_isinstance = ASSERTIONS_MAP["assertIsInstance"]([_arg("obj"), _arg("T")])
    assert _render_assert(t_isinstance) == "assert isinstance(obj, T)"


def test_assert_not_isinstance_and_comparisons() -> None:
    not_instance = ASSERTIONS_MAP["assertNotIsInstance"]([_arg("obj"), _arg("T")])
    assert _render_assert(not_instance) == "assert not isinstance(obj, T)"

    gt = ASSERTIONS_MAP["assertGreater"]([_arg("a"), _arg("b")])
    assert _render_assert(gt) == "assert a > b"

    lt_eq = ASSERTIONS_MAP["assertLessEqual"]([_arg("a"), _arg("b")])
    assert _render_assert(lt_eq) == "assert a <= b"
