"""CstTask units for assertion_rewriter stage.

Provides a single task that applies AssertionRewriter and returns flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, TYPE_CHECKING

import libcst as cst

from ..types import Task, TaskResult, ContextDelta

if TYPE_CHECKING:
    from ..types import Step
from .assertion_rewriter import AssertionRewriter
from .steps_assertion_rewriter import (
    ParseAssertionsStep,
    TransformComparisonAssertionsStep,
    TransformRaisesAssertionsStep,
    TransformComplexAssertionsStep,
    EmitAssertionsStep,
)


DOMAINS = ["stages", "assertions", "tasks"]


@dataclass
class RewriteAssertionsTask(Task):
    id: str = "tasks.assertions.rewrite_assertions"
    name: str = "rewrite_assertions"
    # Expose the pilot Step so tooling can introspect the task. The original
    # execute() method below remains unchanged and serves as the behavioral
    # fallback until we switch to `run_steps` in tests/CI.
    # Pilot exposes a small pipeline of Steps. The original execute() method
    # remains available as a behavioral fallback. When the context contains
    # the flag 'USE_STEPS_REWRITER': True, the Task will execute via
    # run_steps(...) to exercise the Step path.
    steps: Sequence["Step"] = (
        ParseAssertionsStep(),
        TransformComparisonAssertionsStep(),
        TransformRaisesAssertionsStep(),
        TransformComplexAssertionsStep(),
        EmitAssertionsStep(),
    )

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        # Optionally run the new Step pipeline when opted-in via context flag
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return TaskResult(delta=ContextDelta(values={}))

        # Execute the Step pipeline by default. Keep a conservative direct
        # transformer fallback if the runner isn't importable for any reason.
        try:
            from .steps import run_steps

            res = run_steps(
                stage_id="stages.assertion_rewriter",
                task_id=self.id,
                task_name=self.name,
                steps=self.steps,
                context=dict(context),
                resources=resources,
            )
            return TaskResult(delta=res.delta, diagnostics=res.diagnostics, errors=res.errors, skipped=res.skipped)
        except Exception:
            # Fallback to original transformer if run_steps fails unexpectedly.
            transformer = AssertionRewriter()
            new_mod = mod.visit(transformer)
            return TaskResult(
                delta=ContextDelta(
                    values={
                        "module": new_mod,
                        "needs_pytest_import": getattr(transformer, "needs_pytest_import", False),
                        "needs_re_import": getattr(transformer, "needs_re_import", False),
                    }
                )
            )


__all__ = ["RewriteAssertionsTask"]
