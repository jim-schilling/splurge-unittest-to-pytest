"""Adapters to bridge legacy callable stages to Stage/Task contracts.

Publics:
    CallableStage
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ..types import Task, TaskResult, ContextDelta, Stage, StageResult


DOMAINS = ["stages", "adapters", "pipeline"]


StageCallable = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class _TaskAdapter(Task):
    id: str
    name: str
    _fn: StageCallable

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        try:
            # Legacy callable may mutate context or return a mapping
            result = self._fn(dict(context))  # pass a shallow copy for safety
            if isinstance(result, dict):
                return TaskResult(delta=ContextDelta(values=dict(result)))
            return TaskResult(delta=ContextDelta(values={}))
        except Exception as exc:
            return TaskResult(delta=ContextDelta(values={}), errors=[exc])


@dataclass
class CallableStage(Stage):
    id: str
    version: str
    name: str
    _fn: StageCallable

    def __post_init__(self) -> None:
        self.tasks = [_TaskAdapter(id=f"task:{self.name}", name=self.name, _fn=self._fn)]

    def execute(self, context: Mapping[str, Any], resources: Any) -> StageResult:  # type: ignore[override]
        task = self.tasks[0]
        result = task.execute(context, resources)
        return StageResult(delta=result.delta, diagnostics=result.diagnostics, errors=result.errors)


__all__ = ["CallableStage"]
