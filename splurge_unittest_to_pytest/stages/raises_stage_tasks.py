"""CstTask units for raises_stage (Stage-4 decomposition).

Tasks:
  - RewriteRaisesTask: apply RaisesRewriter
  - NormalizeExceptionAttrTask: run ExceptionAttrRewriter over collected names in module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

import libcst as cst

from ..types import ContextDelta, Task, TaskResult

if TYPE_CHECKING:
    from ..types import Step
from .steps import run_steps
from .steps_raises_stage import (
    NormalizeExceptionAttrStep,
    ParseRaisesStep,
    TransformRaisesStep,
)

DOMAINS = ["stages", "raises", "tasks"]


@dataclass
class RewriteRaisesTask(Task):
    id: str = "tasks.raises.rewrite_raises"
    name: str = "rewrite_raises"
    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return TaskResult(delta=ContextDelta(values={}))

        # populate steps lazily to avoid import cycles / work at import time
        if not self.steps:
            try:
                self.steps = [ParseRaisesStep(), TransformRaisesStep()]
            except Exception:
                self.steps = []

        working = dict(context)
        return run_steps(
            stage_id=working.get("__stage_id__", "stages.raises"),
            task_id=self.id,
            task_name=self.name,
            steps=self.steps or [],
            context=working,
            resources=resources,
        )


@dataclass
class NormalizeExceptionAttrTask(Task):
    id: str = "tasks.raises.normalize_exception_attr"
    name: str = "normalize_exception_attr"
    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        maybe_module = context.get("module")
        module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
        if module is None:
            return TaskResult(delta=ContextDelta(values={}))

        # populate steps lazily
        if not self.steps:
            try:
                self.steps = [NormalizeExceptionAttrStep()]
            except Exception:
                self.steps = []

        working = dict(context)
        return run_steps(
            stage_id=working.get("__stage_id__", "stages.raises"),
            task_id=self.id,
            task_name=self.name,
            steps=self.steps or [],
            context=working,
            resources=resources,
        )


__all__ = ["RewriteRaisesTask", "NormalizeExceptionAttrTask"]
