"""Sanity-check generated modules by attempting to reparse their source.

If parsing fails, attach a ``postvalidator_error`` string into the
pipeline context for later inspection.

Publics:
    postvalidator_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import cast

from ..types import PipelineContext

DOMAINS = ["stages", "validation"]
STAGE_ID = "stages.postvalidator"
STAGE_VERSION = "1"

# Associated domains for this module


def postvalidator_stage(context: PipelineContext) -> PipelineContext:
    from .events import EventBus, TaskCompleted, TaskErrored, TaskStarted
    from .postvalidator_tasks import ValidateModuleTask

    stage_id = STAGE_ID
    bus = context.get("__event_bus__")
    task = ValidateModuleTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=task.id))
        res = task.execute(context, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=task.id, error=exc))
        return cast(PipelineContext, {})
    return cast(PipelineContext, res.delta.values)
