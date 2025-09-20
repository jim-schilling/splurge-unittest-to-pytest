"""CstTask for decorator and mock fixes stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, TYPE_CHECKING

import libcst as cst

from ..types import Task, TaskResult, ContextDelta

if TYPE_CHECKING:
    from ..types import Step
from .steps import run_steps
from .steps_decorator_and_mock_fixes import ApplyDecoratorAndMockFixesStep


DOMAINS = ["stages", "mocks", "tasks"]


@dataclass
class ApplyDecoratorAndMockFixesTask(Task):
    id: str = "tasks.mocks.apply_decorator_and_mock_fixes"
    name: str = "apply_decorator_and_mock_fixes"
    # Expose underlying Steps for tooling and introspection
    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return TaskResult(delta=ContextDelta(values={}))
        # populate steps lazily (empty sequence indicates uninitialized)
        if not self.steps:
            try:
                self.steps = [ApplyDecoratorAndMockFixesStep()]
            except Exception:
                self.steps = []
        working = dict(context)
        return run_steps(
            stage_id=working.get("__stage_id__", "stages.mocks"),
            task_id=self.id,
            task_name=self.name,
            steps=self.steps or [],
            context=working,
            resources=resources,
        )


__all__ = ["ApplyDecoratorAndMockFixesTask"]
