"""Step implementations for the assertion_rewriter stage.

This module provides a thin Step wrapper that invokes the existing
AssertionRewriter transformer and returns a StepResult. The pilot starts
with a single Step that preserves the Task behaviour; future work will
break this into multiple, smaller Steps.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import libcst as cst

from ..types import StepResult, ContextDelta
from .assertion_rewriter import AssertionRewriter
from libcst import CSTVisitor


class _FindSelfAssertVisitor(CSTVisitor):
    def __init__(self) -> None:
        self.calls: list[cst.Call] = []

    def visit_Call(self, node: cst.Call) -> None:  # type: ignore[override]
        try:
            func = node.func
            if isinstance(func, cst.Attribute) and isinstance(func.value, cst.Name) and func.value.value == "self":
                if func.attr.value.startswith("assert"):
                    self.calls.append(node)
        except Exception:
            pass


class RunAssertionRewriterStep:
    id = "steps.assertions.run_rewriter"
    name = "run_assertion_rewriter"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))
        transformer = AssertionRewriter()
        new_mod = mod.visit(transformer)
        return StepResult(
            delta=ContextDelta(
                values={
                    "module": new_mod,
                    "needs_pytest_import": getattr(transformer, "needs_pytest_import", False),
                    "needs_re_import": getattr(transformer, "needs_re_import", False),
                }
            )
        )


class ParseAssertionsStep:
    id = "steps.assertions.parse"
    name = "parse_assertions"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))
        visitor = _FindSelfAssertVisitor()
        try:
            mod.visit(visitor)
        except Exception:
            # conservative: if parsing failed, return an error in StepResult
            from ..types import StepResult as _SR, ContextDelta as _CD

            return _SR(delta=_CD(values={}), errors=[RuntimeError("parse failed")])
        # Serialize calls as simple identifiers (method names) for now
        snippets: list[str] = []
        for c in visitor.calls:
            try:
                func = c.func
                if isinstance(func, cst.Attribute) and isinstance(func.attr, cst.Name):
                    snippets.append(func.attr.value)
                else:
                    snippets.append(repr(func))
            except Exception:
                snippets.append("<unknown>")
        return StepResult(delta=ContextDelta(values={"module": mod, "assertions_parsed": snippets}))


class TransformComparisonAssertionsStep:
    id = "steps.assertions.transform_comparison"
    name = "transform_assertions_comparison"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))

        class ComparisonRewriter(AssertionRewriter):
            def _convert_assertion(self, method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:  # type: ignore[override]
                comparison_methods = {
                    "assertEqual",
                    "assertEquals",
                    "assertNotEqual",
                    "assertNotEquals",
                    "assertIsNone",
                    "assertIsNotNone",
                    "assertIn",
                    "assertNotIn",
                    "assertIs",
                    "assertIsNot",
                    "assertGreater",
                    "assertGreaterEqual",
                    "assertLess",
                    "assertLessEqual",
                    "assertListEqual",
                    "assertDictEqual",
                    "assertSequenceEqual",
                    "assertSetEqual",
                    "assertCountEqual",
                    "assertItemsEqual",
                    "assertMultiLineEqual",
                }
                if method_name in comparison_methods:
                    return super()._convert_assertion(method_name, args)
                return None

        transformer = ComparisonRewriter()
        new_mod = mod.visit(transformer)
        needs_pytest = bool(context.get("needs_pytest_import", False)) or bool(
            getattr(transformer, "needs_pytest_import", False)
        )
        needs_re = bool(context.get("needs_re_import", False)) or bool(getattr(transformer, "needs_re_import", False))
        return StepResult(
            delta=ContextDelta(
                values={
                    "module": new_mod,
                    "assertions_transformed_comparison": True,
                    "needs_pytest_import": needs_pytest,
                    "needs_re_import": needs_re,
                }
            )
        )


class TransformComplexAssertionsStep:
    """Compatibility wrapper that runs the original AssertionRewriter.

    Some tests and tooling still import/expect TransformComplexAssertionsStep;
    provide this thin wrapper so the new focused Steps can coexist while
    preserving the original monolithic behaviour when requested.
    """

    id = "steps.assertions.transform_complex"
    name = "transform_assertions_complex"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))

        transformer = AssertionRewriter()
        new_mod = mod.visit(transformer)
        return StepResult(
            delta=ContextDelta(
                values={
                    "module": new_mod,
                    "assertions_transformed_complex": True,
                    "needs_pytest_import": getattr(transformer, "needs_pytest_import", False),
                    "needs_re_import": getattr(transformer, "needs_re_import", False),
                }
            )
        )


class TransformAlmostEqualAssertionsStep:
    id = "steps.assertions.transform_almost_equal"
    name = "transform_assertions_almost_equal"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))

        class AlmostEqualRewriter(AssertionRewriter):
            def _convert_assertion(self, method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:  # type: ignore[override]
                if method_name in ("assertAlmostEqual", "assertNotAlmostEqual", "assertAlmostEquals"):
                    return super()._convert_assertion(method_name, args)
                return None

        transformer = AlmostEqualRewriter()
        new_mod = mod.visit(transformer)
        needs_pytest = bool(context.get("needs_pytest_import", False)) or bool(
            getattr(transformer, "needs_pytest_import", False)
        )
        return StepResult(
            delta=ContextDelta(
                values={"module": new_mod, "assertions_transformed_almost": True, "needs_pytest_import": needs_pytest}
            )
        )


class TransformRegexAssertionsStep:
    id = "steps.assertions.transform_regex"
    name = "transform_assertions_regex"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))

        class RegexRewriter(AssertionRewriter):
            def _convert_assertion(self, method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:  # type: ignore[override]
                if method_name in ("assertRegex", "assertNotRegex", "assertRegexpMatches", "assertNotRegexpMatches"):
                    return super()._convert_assertion(method_name, args)
                return None

        transformer = RegexRewriter()
        new_mod = mod.visit(transformer)
        needs_re = bool(context.get("needs_re_import", False)) or bool(getattr(transformer, "needs_re_import", False))
        return StepResult(
            delta=ContextDelta(
                values={"module": new_mod, "assertions_transformed_regex": True, "needs_re_import": needs_re}
            )
        )


class TransformTruthinessAssertionsStep:
    id = "steps.assertions.transform_truthiness"
    name = "transform_assertions_truthiness"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))

        class TruthinessRewriter(AssertionRewriter):
            def _convert_assertion(self, method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:  # type: ignore[override]
                if method_name in ("assertTrue", "assertFalse"):
                    return super()._convert_assertion(method_name, args)
                return None

        transformer = TruthinessRewriter()
        new_mod = mod.visit(transformer)
        return StepResult(delta=ContextDelta(values={"module": new_mod, "assertions_transformed_truthiness": True}))


class TransformIsInstanceAssertionsStep:
    id = "steps.assertions.transform_isinstance"
    name = "transform_assertions_isinstance"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))

        class IsInstanceRewriter(AssertionRewriter):
            def _convert_assertion(self, method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:  # type: ignore[override]
                if method_name in ("assertIsInstance", "assertNotIsInstance"):
                    return super()._convert_assertion(method_name, args)
                return None

        transformer = IsInstanceRewriter()
        new_mod = mod.visit(transformer)
        return StepResult(delta=ContextDelta(values={"module": new_mod, "assertions_transformed_isinstance": True}))


class TransformRaisesAssertionsStep:
    id = "steps.assertions.transform_raises"
    name = "transform_assertions_raises"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        """Placeholder for transforming raises/assertRaises style assertions.

        Currently a no-op that preserves the module. We'll implement
        targeted transformations here in future commits.
        """
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))

        # Focused rewriter that only converts assertRaises-style contexts
        class RaisesOnlyRewriter(AssertionRewriter):
            # prevent expression-level conversions (leave_With from parent will run)
            def leave_Expr(self, original_node: cst.Expr, updated_node: cst.Expr) -> cst.BaseSmallStatement | cst.Expr:  # type: ignore[override]
                return updated_node

        transformer = RaisesOnlyRewriter()
        new_mod = mod.visit(transformer)

        # Ensure we signal pytest import necessity if any pytest.raises calls were generated
        class _FindPytestRaises(cst.CSTVisitor):
            def __init__(self) -> None:
                self.found = False

            def visit_Call(self, node: cst.Call) -> None:  # type: ignore[override]
                try:
                    func = node.func
                    if (
                        isinstance(func, cst.Attribute)
                        and isinstance(func.value, cst.Name)
                        and func.value.value == "pytest"
                    ):
                        if isinstance(func.attr, cst.Name) and func.attr.value == "raises":
                            self.found = True
                except Exception:
                    pass

        visitor = _FindPytestRaises()
        try:
            new_mod.visit(visitor)
        except Exception:
            pass

        needs_pytest = bool(getattr(transformer, "needs_pytest_import", False)) or visitor.found
        return StepResult(
            delta=ContextDelta(
                values={"module": new_mod, "assertions_transformed_raises": True, "needs_pytest_import": needs_pytest}
            )
        )


# Complex-only rewriter was split into smaller focused steps above.


class EmitAssertionsStep:
    id = "steps.assertions.emit"
    name = "emit_assertions"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))
        # Record emitted module code for easier comparisons in tests
        try:
            code = mod.code
        except Exception:
            code = None
        return StepResult(delta=ContextDelta(values={"module": mod, "emitted_nodes": True, "emitted_code": code}))


__all__ = ["RunAssertionRewriterStep"]
