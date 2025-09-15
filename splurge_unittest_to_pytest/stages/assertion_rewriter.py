"""Assertion rewriter stage: convert self.assert* calls to pytest-style asserts
and convert assertRaises context managers to pytest.raises.

This is a focused stage (subset of the legacy transformer's behavior) used
to migrate assertion rewriting into the staged pipeline.
"""

from __future__ import annotations

from typing import Sequence, Optional, Any, cast

import libcst as cst

DOMAINS = ["stages", "assertions", "rewriter"]

# Associated domains for this module
# Moved to top of module after imports.


class AssertionRewriter(cst.CSTTransformer):
    """Transformer that rewrites unittest-style assertions to pytest asserts."""

    def __init__(self) -> None:
        super().__init__()
        self.needs_pytest_import = False

    def leave_Expr(self, original_node: cst.Expr, updated_node: cst.Expr) -> cst.BaseSmallStatement | cst.Expr:
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
    def _is_self_call(self, call_node: cst.Call) -> Optional[tuple[str, Sequence[cst.Arg]]]:
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
        # include older alias assertRaisesRegexp
        return method_name in ("assertRaises", "assertRaisesRegex", "assertRaisesRegexp")

    def _convert_self_assertion_to_pytest(self, call_node: cst.Call) -> Optional[cst.BaseSmallStatement]:
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
                "assertEquals": self._assert_equal,
                "assertNotEqual": self._assert_not_equal,
                "assertNotEquals": self._assert_not_equal,
                "assertTrue": self._assert_true,
                "assertFalse": self._assert_false,
                "assertIsNone": self._assert_is_none,
                "assertIsNotNone": self._assert_is_not_none,
                "assertIn": self._assert_in,
                "assertNotIn": self._assert_not_in,
                "assertIsInstance": self._assert_is_instance,
                "assertIs": self._assert_is,
                "assertIsNot": self._assert_is_not,
                "assertNotIsInstance": self._assert_not_is_instance,
                "assertAlmostEqual": self._assert_almost_equal,
                "assertNotAlmostEqual": self._assert_not_almost_equal,
                "assertAlmostEquals": self._assert_almost_equal,
                "assertListEqual": self._assert_collection_equal,
                "assertDictEqual": self._assert_collection_equal,
                "assertSequenceEqual": self._assert_collection_equal,
                "assertSetEqual": self._assert_collection_equal,
                "assertCountEqual": self._assert_collection_equal,
                "assertItemsEqual": self._assert_collection_equal,
                "assertGreater": self._assert_greater,
                "assertGreaterEqual": self._assert_greater_equal,
                "assertLess": self._assert_less,
                "assertLessEqual": self._assert_less_equal,
                # regex and multi-line comparisons
                "assertRegex": self._assert_regex,
                "assertNotRegex": self._assert_not_regex,
                "assertRegexpMatches": self._assert_regex,
                "assertNotRegexpMatches": self._assert_not_regex,
                "assertMultiLineEqual": self._assert_multi_line_equal,
            }
            converter = assertions_map.get(method_name)
            if converter:
                # strip optional trailing `msg` positional or keyword arg per request
                cleaned_args = list(args)
                # remove any keyword arg named 'msg'
                cleaned_args = [a for a in cleaned_args if not (a.keyword and a.keyword.value == "msg")]
                # If there's an extra trailing positional arg that is intended as a 'msg',
                # we attempt to detect and drop it for converters that expect fewer args.
                # Specific handling for assertAlmostEqual: if a third positional is numeric,
                # treat it as 'places' and keep it; otherwise drop trailing positional extras.
                if method_name in ("assertAlmostEqual", "assertNotAlmostEqual"):
                    # keep first two, then examine third positional (if any)
                    pos_args = [a for a in cleaned_args if a.keyword is None]
                    if len(pos_args) > 2:
                        third = pos_args[2]
                        # if third is a numeric literal, keep it as 'places'
                        if not isinstance(third.value, (cst.Integer, cst.Float)):
                            # drop as probable msg
                            # remove the third positional from cleaned_args
                            # find its index in cleaned_args and pop
                            for i, a in enumerate(cleaned_args):
                                if a is third:
                                    cleaned_args.pop(i)
                                    break
                    else:
                        # nothing to do
                        pass
                else:
                    # Drop any extra positional args beyond what's needed by converter
                    # Conservative approach: if converter expects 2 and we have >2, drop extras
                    # (most converters check len(args) themselves, so this is safe.)
                    pass

                return converter(cleaned_args)
        except Exception:
            return None
        return None

    # Basic converters
    def _assert_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_true(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                return cst.Assert(test=args[0].value)
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_false(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=args[0].value))
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_is_none(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                left_expr = args[0].value
                if isinstance(left_expr, (cst.Integer, cst.Float, cst.SimpleString)):
                    return None
                return cst.Assert(
                    test=cst.Comparison(
                        left=left_expr,
                        comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name("None"))],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_is_not_none(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 1:
                left_expr = args[0].value
                return cst.Assert(
                    test=cst.Comparison(
                        left=left_expr,
                        comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_in(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_almost_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            # Support forms: assertAlmostEqual(a, b), assertAlmostEqual(a, b, delta=..., places=...)
            if len(args) >= 2:
                left = args[0].value
                right = args[1].value
                # examine kwargs in further args for 'delta' or 'places'
                delta_arg: Optional[cst.BaseExpression] = None
                places_arg: Optional[cst.BaseExpression] = None
                # first check for a numeric third positional (treated as 'places')
                if len(args) >= 3 and args[2].keyword is None and isinstance(args[2].value, (cst.Integer, cst.Float)):
                    places_arg = args[2].value
                # then inspect keyword args for explicit delta/places
                for a in args[2:]:
                    try:
                        if a.keyword and a.keyword.value == "delta":
                            delta_arg = a.value
                        if a.keyword and a.keyword.value == "places":
                            places_arg = a.value
                    except Exception:
                        pass
                if delta_arg is not None:
                    # map to abs(left - right) <= delta
                    abs_call = cst.Call(
                        func=cst.Name("abs"),
                        args=[cst.Arg(value=cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right))],
                    )
                    le_compare = cst.Comparison(
                        left=abs_call,
                        comparisons=[cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=delta_arg)],
                    )
                    return cst.Assert(test=le_compare)
                if places_arg is not None:
                    # map to round(left - right, places) == 0
                    diff = cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right)
                    round_call = cst.Call(func=cst.Name("round"), args=[cst.Arg(value=diff), cst.Arg(value=places_arg)])
                    return cst.Assert(
                        test=cst.Comparison(
                            left=round_call,
                            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer("0"))],
                        )
                    )
                # default: use pytest.approx
                self.needs_pytest_import = True
                approx_call = cst.Call(
                    func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("approx")), args=[cst.Arg(value=right)]
                )
                return cst.Assert(
                    test=cst.Comparison(
                        left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=approx_call)]
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_almost_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                left = args[0].value
                right = args[1].value
                # check for delta/places kwargs (and numeric third positional as places)
                delta_arg: Optional[cst.BaseExpression] = None
                places_arg: Optional[cst.BaseExpression] = None
                if len(args) >= 3 and args[2].keyword is None and isinstance(args[2].value, (cst.Integer, cst.Float)):
                    places_arg = args[2].value
                for a in args[2:]:
                    try:
                        if a.keyword and a.keyword.value == "delta":
                            delta_arg = a.value
                        if a.keyword and a.keyword.value == "places":
                            places_arg = a.value
                    except Exception:
                        pass
                if delta_arg is not None:
                    abs_call = cst.Call(
                        func=cst.Name("abs"),
                        args=[cst.Arg(value=cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right))],
                    )
                    gt_compare = cst.Comparison(
                        left=abs_call,
                        comparisons=[cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=delta_arg)],
                    )
                    return cst.Assert(test=gt_compare)
                if places_arg is not None:
                    diff = cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right)
                    round_call = cst.Call(func=cst.Name("round"), args=[cst.Arg(value=diff), cst.Arg(value=places_arg)])
                    # prefer explicit 'round(...) != 0' over 'not round(...) == 0'
                    return cst.Assert(
                        test=cst.Comparison(
                            left=round_call,
                            comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=cst.Integer("0"))],
                        )
                    )
                # default: use pytest.approx
                self.needs_pytest_import = True
                approx_call = cst.Call(
                    func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("approx")), args=[cst.Arg(value=right)]
                )
                # prefer explicit 'left != pytest.approx(right)'
                return cst.Assert(
                    test=cst.Comparison(
                        left=left, comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=approx_call)]
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_in(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.NotIn(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_is_instance(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                isinstance_call = cst.Call(func=cst.Name("isinstance"), args=[args[0], args[1]])
                return cst.Assert(test=isinstance_call)
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_is(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                left = args[0].value
                right = args[1].value
                return cst.Assert(
                    test=cst.Comparison(
                        left=left, comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=right)]
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_is_not(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                left = args[0].value
                right = args[1].value
                return cst.Assert(
                    test=cst.Comparison(
                        left=left, comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=right)]
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_is_instance(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                isinstance_call = cst.Call(func=cst.Name("isinstance"), args=[args[0], args[1]])
                return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=isinstance_call))
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_greater(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_greater_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.GreaterThanEqual(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_less(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.LessThan(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_less_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_collection_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            # Map collection equality-like asserts to simple equality comparison
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_regex(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            # map assertRegex(text, pattern) -> assert re.search(pattern, text)
            if len(args) >= 2:
                text = args[0].value
                pattern = args[1].value
                # ensure we will import re at module level
                setattr(self, "needs_re_import", True)
                search_call = cst.Call(
                    func=cst.Attribute(value=cst.Name("re"), attr=cst.Name("search")),
                    args=[cst.Arg(value=pattern), cst.Arg(value=text)],
                )
                return cst.Assert(test=search_call)
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_not_regex(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            if len(args) >= 2:
                text = args[0].value
                pattern = args[1].value
                setattr(self, "needs_re_import", True)
                search_call = cst.Call(
                    func=cst.Attribute(value=cst.Name("re"), attr=cst.Name("search")),
                    args=[cst.Arg(value=pattern), cst.Arg(value=text)],
                )
                # prefer explicit comparison 're.search(...) is None' over unary 'not re.search(...)'
                return cst.Assert(
                    test=cst.Comparison(
                        left=search_call,
                        comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name("None"))],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    def _assert_multi_line_equal(self, args: Sequence[cst.Arg]) -> cst.Assert | None:
        try:
            # map to normal equality; multi-line diffs are handled by pytest's assert rewriter
            if len(args) >= 2:
                return cst.Assert(
                    test=cst.Comparison(
                        left=args[0].value,
                        comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)],
                    )
                )
        except Exception:
            pass
        return cst.Assert(test=cst.Name("False"))

    # assertRaises helpers
    def _is_assert_raises_context_manager(self, call_node: cst.Call) -> str | None:
        call_info = self._is_self_call(call_node)
        if call_info:
            method_name, _ = call_info
            if method_name in ("assertRaises", "assertRaisesRegex"):
                return method_name
        return None

    def _create_pytest_raises_item(self, method_name: str, args: Sequence[cst.Arg]) -> cst.WithItem:
        # creation of a pytest.raises call implies we'll need pytest imported
        try:
            self.needs_pytest_import = True
        except Exception:
            pass

        if method_name == "assertRaises":
            return cst.WithItem(
                item=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")), args=list(args))
            )
        else:
            # assertRaisesRegex -> pytest.raises(..., match=...)
            if len(args) >= 2:
                return cst.WithItem(
                    item=cst.Call(
                        func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")),
                        args=[args[0], cst.Arg(keyword=cst.Name("match"), value=args[1].value)],
                    )
                )
        return cst.WithItem(
            item=cst.Call(func=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("raises")), args=list(args))
        )


def assertion_rewriter_stage(context: dict[str, Any]) -> dict[str, Any]:
    module = context.get("module")
    if module is None:
        return {}
    module = cast(cst.Module, module)
    transformer = AssertionRewriter()
    new_mod = module.visit(transformer)
    return {
        "module": new_mod,
        "needs_pytest_import": getattr(transformer, "needs_pytest_import", False),
        "needs_re_import": getattr(transformer, "needs_re_import", False),
    }
