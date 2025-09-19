from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..types import Step, StepResult, TaskResult, ContextDelta
from .events import EventBus, StepStarted, StepCompleted, StepErrored
from .events import HookRegistry
from . import diagnostics as _diagnostics


def run_steps(
    stage_id: str,
    task_id: str,
    task_name: str,
    steps: Sequence[Step],
    context: Mapping[str, Any],
    resources: Any,
) -> TaskResult:
    """Execute steps in order, folding deltas, emitting events and hooks.

    Temporary values stored under the key "__tmp_step__" are not surfaced in
    the returned TaskResult delta.
    """

    working = dict(context)
    bus = working.get("__event_bus__")
    hooks = working.get("__hooks__")
    if not isinstance(stage_id, str) or not stage_id:
        stage_id = "stages.unknown"
    # Suppress step events unless diagnostics are enabled globally
    emit_step_events = False
    try:
        emit_step_events = bool(_diagnostics.diagnostics_enabled())
    except Exception:
        emit_step_events = False
    agg: dict[str, Any] = {}
    errors: list[Exception] = []
    diagnostics: dict[str, Any] = {}
    for step in steps:
        try:
            if emit_step_events and isinstance(bus, EventBus):
                bus.publish(StepStarted(run_id="", stage_id=stage_id, task_id=task_id, step_id=step.id))
            if isinstance(hooks, HookRegistry):
                try:
                    hooks.before_step(task_name, step.name, dict(working))
                except Exception:
                    pass
            res: StepResult = step.execute(working, resources)
            delta_vals = dict(res.delta.values)
            working.update(delta_vals)
            for k, v in delta_vals.items():
                if k == "__tmp_step__" or k.startswith("__tmp_step__"):
                    continue
                agg[k] = v
            diagnostics.update(res.diagnostics)
            if isinstance(hooks, HookRegistry):
                try:
                    hooks.after_step(task_name, step.name, dict(res.delta.values))
                except Exception:
                    pass
            if emit_step_events and isinstance(bus, EventBus):
                bus.publish(StepCompleted(run_id="", stage_id=stage_id, task_id=task_id, step_id=step.id))
        except Exception as exc:
            errors.append(exc)
            if emit_step_events and isinstance(bus, EventBus):
                try:
                    bus.publish(StepErrored(run_id="", stage_id=stage_id, task_id=task_id, step_id=step.id, error=exc))
                except Exception:
                    pass
            break
    return TaskResult(delta=ContextDelta(values=agg), diagnostics=diagnostics, errors=errors)


__all__ = ["run_steps"]
