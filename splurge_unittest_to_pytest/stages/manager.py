"""StageManager skeleton for orchestrating converter stages.

This minimal manager supports registering callables that accept and return a
`context` mapping. The context starts with the `module` (cst.Module) and may be
extended with stage outputs (e.g., collector_output).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

import libcst as cst

StageCallable = Callable[[Dict[str, Any]], Dict[str, Any]]


class StageManager:
    def __init__(self, stages: List[StageCallable] | None = None) -> None:
        self.stages: List[StageCallable] = stages or []

    def register(self, stage: StageCallable) -> None:
        self.stages.append(stage)

    def run(self, module: cst.Module) -> Dict[str, Any]:
        context: Dict[str, Any] = {"module": module}
        for stage in self.stages:
            result = stage(context)
            # allow stages to either mutate context in-place or return a new
            # dict with their outputs; merge conservatively
            if result is None:
                continue
            if isinstance(result, dict):
                context.update(result)
        return context
