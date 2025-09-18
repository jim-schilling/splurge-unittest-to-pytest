"""CstTask for decorator and mock fixes stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from ..types import Task, TaskResult, ContextDelta
from .decorator_and_mock_fixes import DecoratorAndMockTransformer


DOMAINS = ["stages", "mocks", "tasks"]


@dataclass
class ApplyDecoratorAndMockFixesTask(Task):
    id: str = "tasks.mocks.apply_decorator_and_mock_fixes"
    name: str = "apply_decorator_and_mock_fixes"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return TaskResult(delta=ContextDelta(values={}))
        transformer = DecoratorAndMockTransformer()
        new_mod = mod.visit(transformer)
        return TaskResult(delta=ContextDelta(values={"module": new_mod}))


__all__ = ["ApplyDecoratorAndMockFixesTask"]
