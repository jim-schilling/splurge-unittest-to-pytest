"""CstTask units for tidy stage.

Tasks:
  - NormalizeSpacingTask: ensure two EmptyLines before top-level defs/classes
  - EnsureSelfParamTask: add self param to class test methods missing params
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast


from ..types import Task, TaskResult
from .steps import run_steps


DOMAINS = ["stages", "tidy", "tasks"]


@dataclass
class NormalizeSpacingTask(Task):
    id: str = "tasks.tidy.normalize_spacing"
    name: str = "normalize_spacing"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        from .steps_tidy import NormalizeSpacingStep

        stage_id = cast(str, context.get("__stage_id__", "stages.tidy"))
        task_id = self.id
        task_name = self.name
        steps = [NormalizeSpacingStep()]
        return run_steps(stage_id, task_id, task_name, steps, context, resources)


@dataclass
class EnsureSelfParamTask(Task):
    id: str = "tasks.tidy.ensure_self_param"
    name: str = "ensure_self_param"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        from .steps_tidy import EnsureSelfParamStep

        stage_id = cast(str, context.get("__stage_id__", "stages.tidy"))
        task_id = self.id
        task_name = self.name
        steps = [EnsureSelfParamStep()]
        return run_steps(stage_id, task_id, task_name, steps, context, resources)


__all__ = ["NormalizeSpacingTask", "EnsureSelfParamTask"]
