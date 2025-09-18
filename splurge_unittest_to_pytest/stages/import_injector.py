"""Deterministically ensure required imports exist in a module.

This stage inspects the pipeline context for flags such as
``needs_pytest_import`` or a set of ``needs_typing_names`` and
inserts minimal import statements at a deterministic location in the
module (after the docstring or existing imports). The injector avoids
duplicating existing imports and will merge or create a single
``from typing import ...`` statement when typing names are requested.

Publics:
    import_injector_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Optional, Any, cast
from ..types import PipelineContext
from .import_injector_tasks import DetectNeedsCstTask, InsertImportsCstTask
from .events import EventBus, TaskStarted, TaskCompleted, TaskErrored

import libcst as cst

DOMAINS = ["stages", "imports"]
STAGE_ID = "stages.import_injector"
STAGE_VERSION = "1"

# Associated domains for this module


def import_injector_stage(context: PipelineContext) -> PipelineContext:
    """Pipeline stage that ensures required imports exist in the module.

    Inspects context flags (for example ``needs_pytest_import``) and scans
    the module to detect and insert required imports deterministically.
    """

    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return cast(PipelineContext, {})

    # Stage-2 pilot: run two small CstTasks to determine needs and insert imports.
    stage_id = "stages.import_injector"
    bus = context.get("__event_bus__")
    hooks: Any = context.get("__hooks__")

    needs_task = DetectNeedsCstTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=needs_task.id))
        if hooks is not None:
            try:
                hooks.before_task(stage_id, needs_task.name, dict(context))
            except Exception:
                pass
        needs_result = needs_task.execute(context, resources=None)
        if hooks is not None:
            try:
                hooks.after_task(stage_id, needs_task.name, dict(needs_result.delta.values))
            except Exception:
                pass
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=needs_task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=needs_task.id, error=exc))
        return cast(PipelineContext, {"module": module})

    # merge deltas into a temp mapping for the insert task
    tmp_ctx = dict(context)
    tmp_ctx.update(needs_result.delta.values)

    insert_task = InsertImportsCstTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=insert_task.id))
        if hooks is not None:
            try:
                hooks.before_task(stage_id, insert_task.name, dict(tmp_ctx))
            except Exception:
                pass
        insert_result = insert_task.execute(tmp_ctx, resources=None)
        if hooks is not None:
            try:
                hooks.after_task(stage_id, insert_task.name, dict(insert_result.delta.values))
            except Exception:
                pass
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=insert_task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=insert_task.id, error=exc))
        return cast(PipelineContext, {"module": module})

    return cast(PipelineContext, insert_result.delta.values)
