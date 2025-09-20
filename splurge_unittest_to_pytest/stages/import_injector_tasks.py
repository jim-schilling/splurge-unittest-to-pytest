"""Taskized implementation pieces for the import injector stage (pilot).

Provides two small `CstTask`-style tasks used by `import_injector_stage`:
    - DetectNeedsCstTask: determine which imports are needed based on context and module text
    - InsertImportsCstTask: insert imports deterministically given the needs flags

These tasks are internal to the stage and preserve existing behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence, cast

import libcst as cst

from ..types import ContextDelta, Task, TaskResult

if TYPE_CHECKING:
    from ..types import Step
from .steps import run_steps

DOMAINS = ["stages", "imports", "tasks"]


def _get_module(context: Mapping[str, Any]) -> cst.Module | None:
    mod = context.get("module")
    return mod if isinstance(mod, cst.Module) else None


@dataclass
class DetectNeedsCstTask(Task):
    id: str = "tasks.import_injector.detect_needs"
    name: str = "detect_needs"
    # Expose underlying Step(s) for tooling: this Task delegates to DetectNeedsStep
    steps: Sequence["Step"] = ()  # filled at runtime to avoid import cycles

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        module = _get_module(context)
        if module is None:
            return TaskResult(delta=ContextDelta(values={}))

        from .steps_import_injector import DetectNeedsStep

        # populate steps attribute lazily (empty sequence indicates uninitialized)
        if not self.steps:
            try:
                self.steps = [DetectNeedsStep()]
            except Exception:
                self.steps = []

        stage_id = cast(str, context.get("__stage_id__", "stages.import_injector"))
        task_id = self.id
        task_name = self.name
        steps = [DetectNeedsStep()]
        return run_steps(stage_id, task_id, task_name, steps, context, resources)


@dataclass
class InsertImportsCstTask(Task):
    id: str = "tasks.import_injector.insert_imports"
    name: str = "insert_imports"
    # Expose underlying Step(s) for tooling: this Task delegates to InsertImportsStep
    steps: Sequence["Step"] = ()  # filled at runtime to avoid import cycles

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        module = _get_module(context)
        if module is None:
            return TaskResult(delta=ContextDelta(values={}))

        from .steps_import_injector import InsertImportsStep

        # populate steps attribute lazily (empty sequence indicates uninitialized)
        if not self.steps:
            try:
                self.steps = [InsertImportsStep()]
            except Exception:
                self.steps = []

        stage_id = cast(str, context.get("__stage_id__", "stages.import_injector"))
        task_id = self.id
        task_name = self.name
        steps = [InsertImportsStep()]
        return run_steps(stage_id, task_id, task_name, steps, context, resources)


__all__ = ["DetectNeedsCstTask", "InsertImportsCstTask"]
