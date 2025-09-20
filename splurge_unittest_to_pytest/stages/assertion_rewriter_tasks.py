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
from .steps_assertion_rewriter import RunAssertionRewriterStep


DOMAINS = ["stages", "assertions", "tasks"]


@dataclass
class RewriteAssertionsTask(Task):
    id: str = "tasks.assertions.rewrite_assertions"
    name: str = "rewrite_assertions"
    # Expose the pilot Step so tooling can introspect the task. The original
    # execute() method below remains unchanged and serves as the behavioral
    # fallback until we switch to `run_steps` in tests/CI.
    steps: Sequence["Step"] = (RunAssertionRewriterStep(),)

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return TaskResult(delta=ContextDelta(values={}))
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
