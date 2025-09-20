"""Remove unittest imports, TestCase bases, and test-run guards.

Strips top-level ``unittest`` imports, removes ``TestCase`` bases from
classes, and drops common ``if __name__ == '__main__'`` test-run guards.

Publics:
    remove_unittest_artifacts_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import cast

from ..types import PipelineContext

DOMAINS = ["stages", "helpers"]
STAGE_ID = "stages.remove_unittest_artifacts"
STAGE_VERSION = "1"

# Associated domains for this module


def remove_unittest_artifacts_stage(context: PipelineContext) -> PipelineContext:
    from .events import EventBus, TaskCompleted, TaskErrored, TaskStarted
    from .remove_unittest_artifacts_tasks import RemoveUnittestArtifactsTask

    stage_id = STAGE_ID
    bus = context.get("__event_bus__")
    task = RemoveUnittestArtifactsTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=task.id))
        res = task.execute(context, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=task.id, error=exc))
        return cast(PipelineContext, {"module": context.get("module")})
    return cast(PipelineContext, res.delta.values)
