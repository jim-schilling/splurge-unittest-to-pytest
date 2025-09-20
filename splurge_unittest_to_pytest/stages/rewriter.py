"""Rewriter stage: update class test method signatures for fixtures.

Uses collector metadata to decide whether to remove the leading
``self``/``cls`` parameter and append fixture parameters inferred from
``setUp`` assignments. Operates as a :class:`libcst.CSTTransformer` that
visits class and function definitions and adjusts parameter lists.

Publics:
    rewriter_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Optional, cast

import libcst as cst

from ..types import PipelineContext
from .events import EventBus, TaskCompleted, TaskErrored, TaskStarted
from .rewriter_tasks import RewriteTestMethodParamsTask

DOMAINS = ["stages", "rewriter"]

# Associated domains for this module


def rewriter_stage(context: PipelineContext) -> PipelineContext:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None or context.get("collector_output") is None:
        return cast(PipelineContext, {"module": module})
    stage_id = "stages.rewriter"
    bus = context.get("__event_bus__")
    task = RewriteTestMethodParamsTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=task.id))
        res = task.execute(context, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=task.id, error=exc))
        return cast(PipelineContext, {"module": module})
    return cast(PipelineContext, res.delta.values)
