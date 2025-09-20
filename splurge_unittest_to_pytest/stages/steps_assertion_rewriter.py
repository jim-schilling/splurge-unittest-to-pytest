"""Step implementations for the assertion_rewriter stage.

This module provides a thin Step wrapper that invokes the existing
AssertionRewriter transformer and returns a StepResult. The pilot starts
with a single Step that preserves the Task behaviour; future work will
break this into multiple, smaller Steps.
"""

from __future__ import annotations

from typing import Any, Mapping

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
        """Transform simple comparison-style assertions (assertEqual, assertNotEqual, etc.).

        For now this reuses the existing AssertionRewriter but marks the
        delta key so tests can assert which step ran. In future iterations
        this will only apply the comparison-related converters.
        """
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))
        transformer = AssertionRewriter()
        new_mod = mod.visit(transformer)
        return StepResult(
            delta=ContextDelta(
                values={
                    "module": new_mod,
                    "assertions_transformed_comparison": True,
                    "needs_pytest_import": getattr(transformer, "needs_pytest_import", False),
                    "needs_re_import": getattr(transformer, "needs_re_import", False),
                }
            )
        )


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
        return StepResult(delta=ContextDelta(values={"module": mod, "assertions_transformed_raises": True}))


class TransformComplexAssertionsStep:
    id = "steps.assertions.transform_complex"
    name = "transform_assertions_complex"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        # Placeholder for complex transformations (regex, raises, approx)
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))
        # No-op for now; in later iterations this will apply targeted transforms
        return StepResult(delta=ContextDelta(values={"module": mod, "assertions_transformed_complex": True}))


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
