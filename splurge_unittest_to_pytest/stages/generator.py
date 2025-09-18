"""Generate fixture specifications and fixture function nodes.

Consume a :class:`CollectorOutput` and place ``fixture_specs`` and
``fixture_nodes`` into the pipeline context. Detailed inference
(naming, filename inference, bundling) is delegated to helpers under
``stages/generator_parts``.

Publics:
    generator_stage, FixtureSpec

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Any, Optional, cast
from ..types import PipelineContext
from .generator_tasks import BuildFixtureSpecsTask, FinalizeGeneratorTask
from .events import EventBus, TaskStarted, TaskCompleted, TaskErrored

import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.literals import is_literal
from splurge_unittest_to_pytest.stages.collector import CollectorOutput

DOMAINS = ["stages", "generator"]
STAGE_ID = "stages.generator"
STAGE_VERSION = "1"


# Associated domains for this module


def _is_literal(expr: Optional[cst.BaseExpression]) -> bool:
    # keep a thin wrapper to avoid changing existing call sites in this file
    return is_literal(expr)


def generator_stage(context: PipelineContext) -> PipelineContext:
    maybe_out: Any = context.get("collector_output")
    out: Optional[CollectorOutput] = maybe_out if isinstance(maybe_out, CollectorOutput) else None
    if out is None:
        return {}
    stage_id = "stages.generator"
    bus = context.get("__event_bus__")
    # Stage-4: delegate work to tasks and emit per-task events
    build_task = BuildFixtureSpecsTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=build_task.id))
        build_res = build_task.execute(context, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=build_task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=build_task.id, error=exc))
        return {}

    tmp_ctx = dict(context)
    tmp_ctx.update(build_res.delta.values)
    finalize_task = FinalizeGeneratorTask()
    try:
        if isinstance(bus, EventBus):
            bus.publish(TaskStarted(run_id="", stage_id=stage_id, task_id=finalize_task.id))
        fin_res = finalize_task.execute(tmp_ctx, resources=None)
        if isinstance(bus, EventBus):
            bus.publish(TaskCompleted(run_id="", stage_id=stage_id, task_id=finalize_task.id))
    except Exception as exc:
        if isinstance(bus, EventBus):
            bus.publish(TaskErrored(run_id="", stage_id=stage_id, task_id=finalize_task.id, error=exc))
        return {}
    return cast(PipelineContext, fin_res.delta.values)
