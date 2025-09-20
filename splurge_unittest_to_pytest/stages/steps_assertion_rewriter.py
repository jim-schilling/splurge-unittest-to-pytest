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


__all__ = ["RunAssertionRewriterStep"]
