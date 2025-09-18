"""CstTask units for assertion_rewriter stage.

Provides a single task that applies AssertionRewriter and returns flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from ..types import Task, TaskResult, ContextDelta
from .assertion_rewriter import AssertionRewriter


DOMAINS = ["stages", "assertions", "tasks"]


@dataclass
class RewriteAssertionsTask(Task):
    id: str = "tasks.assertions.rewrite_assertions"
    name: str = "rewrite_assertions"

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
