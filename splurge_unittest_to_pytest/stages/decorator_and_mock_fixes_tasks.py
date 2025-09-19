"""CstTask for decorator and mock fixes stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from ..types import Task, TaskResult, ContextDelta, Step
from .steps import run_steps
from .steps_decorator_and_mock_fixes import ApplyDecoratorAndMockFixesStep


DOMAINS = ["stages", "mocks", "tasks"]


@dataclass
class ApplyDecoratorAndMockFixesTask(Task):
    id: str = "tasks.mocks.apply_decorator_and_mock_fixes"
    name: str = "apply_decorator_and_mock_fixes"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return TaskResult(delta=ContextDelta(values={}))
        steps: list[Step] = [ApplyDecoratorAndMockFixesStep()]
        working = dict(context)
        return run_steps(
            stage_id=working.get("__stage_id__", "stages.mocks"),
            task_id=self.id,
            task_name=self.name,
            steps=steps,
            context=working,
            resources=resources,
        )


__all__ = ["ApplyDecoratorAndMockFixesTask"]
