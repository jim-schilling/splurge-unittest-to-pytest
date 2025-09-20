from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


from ..types import Task, TaskResult
from .steps import run_steps

from .steps_rewriter import RewriteMethodParamsStep


@dataclass
class RewriteTestMethodParamsTask(Task):
    id: str = "tasks.rewriter.rewrite_method_params"
    name: str = "rewrite_method_params"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        stage_id = context.get("__stage_id__", "stages.rewriter")
        task_id = self.id
        task_name = self.name
        steps = [RewriteMethodParamsStep()]
        return run_steps(stage_id, task_id, task_name, steps, context, resources)


__all__ = ["RewriteTestMethodParamsTask"]
