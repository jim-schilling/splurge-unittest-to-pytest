"""Assertion rewriter stage: convert self.assert* calls to pytest-style asserts
and convert assertRaises context managers to pytest.raises.

This is a focused stage (subset of the legacy transformer's behavior) used
to migrate assertion rewriting into the staged pipeline.
"""
from __future__ import annotations

from typing import Sequence, Tuple

import libcst as cst


class AssertionRewriter(cst.CSTTransformer):
    """Transformer that rewrites unittest-style assertions to pytest asserts."""

    def __init__(self) -> None:
        super().__init__()
        self.needs_pytest_import = False

    def leave_Expr(self, original_node: cst.Expr, updated_node: cst.Expr):
        # Only handle call expressions like self.assertX(...)
        if isinstance(updated_node.value, cst.Call):
            conv = self._convert_self_assertion_to_pytest(updated_node.value)
            if conv is not None:
                return conv
        return updated_node

    def leave_With(self, original_node: cst.With, updated_node: cst.With) -> cst.With:
        # detect with self.assertRaises(...) as cm:  -> with pytest.raises(...):
        if not updated_node.items:
            return updated_node
        item = updated_node.items[0]
        if not isinstance(item.item, cst.Call):
            return updated_node
        method_name = self._is_assert_raises_context_manager(item.item)
        if method_name:
            new_item = self._create_pytest_raises_item(method_name, item.item.args)
            new_items = [updated_node.items[0].with_changes(item=new_item)] + list(updated_node.items[1:])
            return updated_node.with_changes(items=new_items)
        return updated_node

    # --- helpers (small subset mirrored from legacy transformer) ---
    def _is_self_call(self, call_node: cst.Call) -> Tuple[str, Sequence[cst.Arg]] | None:
        try:
            if isinstance(call_node.func, cst.Attribute):
                if isinstance(call_node.func.value, cst.Name):
                    if call_node.func.value.value == "self":
                        method_name = call_node.func.attr.value
                        return method_name, call_node.args
        except Exception:
            pass
        return None

    def _should_skip_assertion_conversion(self, method_name: str) -> bool:
        return method_name in ("assertRaises", "assertRaisesRegex")

    def _convert_self_assertion_to_pytest(self, call_node: cst.Call) -> cst.BaseSmallStatement | None:
        try:
            call_info = self._is_self_call(call_node)
            if call_info:
                method_name, args = call_info
                if self._should_skip_assertion_conversion(method_name):
                    return None
                return self._convert_assertion(method_name, args)

            if isinstance(call_node.func, cst.Name):
                method_name = call_node.func.value
                if self._should_skip_assertion_conversion(method_name):
                    return None
                return self._convert_assertion(method_name, call_node.args)
        except Exception:
            return None
        return None

    def _convert_assertion(self, method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:
        try:
            assertions_map = {
                "assertEqual": self._assert_equal,
                "assertNotEqual": self._assert_not_equal,
                "assertTrue": self._assert_true,
                "assertFalse": self._assert_false,
                "assertIsNone": self._assert_is_none,
                "assertIsNotNone": self._assert_is_not_none,
                "assertIn": self._assert_in,
                "assertNotIn": self._assert_not_in,
                "assertIsInstance": self._assert_is_instance,
                "assertNotIsInstance": self._assert_not_is_instance,
                "assertAlmostEqual": self._assert_almost_equal,
                "assertNotAlmostEqual": self._assert_not_almost_equal,
                "assertListEqual": self._assert_collection_equal,
                "assertDictEqual": self._assert_collection_equal,
                "assertSequenceEqual": self._assert_collection_equal,
                "assertSetEqual": self._assert_collection_equal,
                "assertCountEqual": self._assert_collection_equal,
                "assertGreater": self._assert_greater,
                "assertGreaterEqual": self._assert_greater_equal,
                "assertLess": self._assert_less,
                "assertLessEqual": self._assert_less_equal,
            }
            converter = assertions_map.get(method_name)
            if converter:
                return converter(args)
        except Exception:
            return None
        return None

    # Basic converters
    def _assert_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_not_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_true(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                return cst.Assert(test=args[0].value)
        except Exception:
            pass
        return None

    def _assert_false(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=args[0].value))
        except Exception:
            pass
        return None

    def _assert_is_none(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                left_expr = args[0].value
                if isinstance(left_expr, (cst.Integer, cst.Float, cst.SimpleString)):
                    return None
                return cst.Assert(test=cst.Comparison(left=left_expr, comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name("None"))]))
        except Exception:
            pass
        return None

    def _assert_is_not_none(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                left_expr = args[0].value
                return cst.Assert(test=cst.Comparison(left=left_expr, comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))]))
        except Exception:
            pass
        return None

    def _assert_in(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_almost_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            # map to assert a == pytest.approx(b)
            if len(args) >= 2:
                left = args[0].value
                right = args[1].value
                # mark that pytest.approx is required
                self.needs_pytest_import = True
                approx_call = cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("approx")), args=[cst.Arg(value=right)])
                return cst.Assert(test=cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=approx_call)]))
        except Exception:
            pass
        return None

    def _assert_not_almost_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                left = args[0].value
                right = args[1].value
                # mark that pytest.approx is required
                self.needs_pytest_import = True
                approx_call = cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("approx")), args=[cst.Arg(value=right)])
                return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=approx_call)])))
        except Exception:
            pass
        return None

    def _assert_not_in(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.NotIn(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_is_instance(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                isinstance_call = cst.Call(func=cst.Name("isinstance"), args=[args[0], args[1]])
                return cst.Assert(test=isinstance_call)
        except Exception:
            pass
        return None

    def _assert_not_is_instance(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                isinstance_call = cst.Call(func=cst.Name("isinstance"), args=[args[0], args[1]])
                return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=isinstance_call))
        except Exception:
            pass
        return None

    def _assert_greater(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_greater_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.GreaterThanEqual(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_less(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.LessThan(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_less_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    def _assert_collection_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            # Map collection equality-like asserts to simple equality comparison
            if len(args) >= 2:
                return cst.Assert(test=cst.Comparison(left=args[0].value, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)]))
        except Exception:
            pass
        return None

    # assertRaises helpers
    def _is_assert_raises_context_manager(self, call_node: cst.Call) -> str | None:
        call_info = self._is_self_call(call_node)
        if call_info:
            method_name, _ = call_info
            if method_name in ("assertRaises", "assertRaisesRegex"):
                return method_name
        return None

    def _create_pytest_raises_item(self, method_name: str, args: Sequence[cst.Arg]) -> cst.WithItem:
        if method_name == "assertRaises":
            return cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")), args=args))
        else:
            # assertRaisesRegex -> pytest.raises(..., match=...)
            if len(args) >= 2:
                return cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")), args=[args[0], cst.Arg(keyword=cst.Name("match"), value=args[1].value)]))
            return cst.WithItem(item=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")), args=args))


def assertion_rewriter_stage(context: dict) -> dict:
    module: cst.Module = context.get("module")
    if module is None:
        return {}
    transformer = AssertionRewriter()
    new_mod = module.visit(transformer)
    return {"module": new_mod, "needs_pytest_import": getattr(transformer, "needs_pytest_import", False)}
