from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from ..types import ContextDelta, Step, StepResult
from .decorator_and_mock_fixes import DecoratorAndMockTransformer

DOMAINS = ["stages", "mocks", "steps"]


@dataclass
class ApplyDecoratorAndMockFixesStep(Step):
    id: str = "steps.mocks.apply_decorator_and_mock_fixes"
    name: str = "apply_decorator_and_mock_fixes"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        mod = context.get("module")
        if not isinstance(mod, cst.Module):
            return StepResult(delta=ContextDelta(values={}))
        transformer = DecoratorAndMockTransformer()
        new_mod = mod.visit(transformer)
        return StepResult(delta=ContextDelta(values={"module": new_mod}))


__all__ = ["ApplyDecoratorAndMockFixesStep"]
