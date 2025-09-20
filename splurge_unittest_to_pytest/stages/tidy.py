"""Final tidy stage: spacing normalization and light post-processing.

Performs the centralized formatting pass using :func:`normalize_module`
and enforces canonical blank-line counts and class-method parameter
expectations. This is the last stage in the pipeline and prepares the
module for output.

Publics:
    tidy_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import cast

from ..types import PipelineContext

DOMAINS = ["stages", "tidy"]
STAGE_ID = "stages.tidy"
STAGE_VERSION = "1"

# Associated domains for this module


def tidy_stage(context: PipelineContext) -> PipelineContext:
    from .events import EventBus, TaskCompleted, TaskErrored, TaskStarted
    from .tidy_tasks import EnsureSelfParamTask, NormalizeSpacingTask

    stage_id = STAGE_ID
    bus = context.get("__event_bus__")
    task1 = NormalizeSpacingTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=task1.id))
        res1 = task1.execute(context, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=task1.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=task1.id, error=exc))
        return cast(PipelineContext, {"module": context.get("module")})

    tmp = dict(context)
    tmp.update(res1.delta.values)
    task2 = EnsureSelfParamTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=task2.id))
        res2 = task2.execute(tmp, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=task2.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=task2.id, error=exc))
        return cast(PipelineContext, res1.delta.values)
    return cast(PipelineContext, res2.delta.values)
