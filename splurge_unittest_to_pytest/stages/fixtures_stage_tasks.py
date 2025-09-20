"""CstTask units for fixtures_stage (Stage-4 decomposition).

Tasks:
  - BuildTopLevelTestsTask: produce top-level pytest test functions from classes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

import libcst as cst

from ..types import ContextDelta, Step, Task, TaskResult
from .collector import CollectorOutput
from .steps import run_steps
from .steps_fixtures_stage import BuildTopLevelFnsStep, CollectClassesStep

DOMAINS = ["stages", "fixtures", "tasks"]


@dataclass
class BuildTopLevelTestsTask(Task):
    id: str = "tasks.fixtures_stage.build_top_level_tests"
    name: str = "build_top_level_tests"
    if TYPE_CHECKING:  # pragma: no cover - typing only
        from ..types import Step  # type: ignore

    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        module: Optional[cst.Module] = context.get("module")
        collector: Optional[CollectorOutput] = context.get("collector_output")
        if module is None or collector is None:
            return TaskResult(delta=ContextDelta(values={"module": module}))

        steps: list[Step] = [CollectClassesStep(), BuildTopLevelFnsStep()]
        working = dict(context)
        return run_steps(
            stage_id=working.get("__stage_id__", "stages.fixtures"),
            task_id=self.id,
            task_name=self.name,
            steps=steps,
            context=working,
            resources=resources,
        )


__all__ = ["BuildTopLevelTestsTask"]
