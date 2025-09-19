from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import logging
import libcst as cst
from ..types import Task, TaskResult, ContextDelta, Step

from .steps import run_steps
from .steps_fixture_injector import (
    FindInsertionIndexStep,
    InsertNodesStep,
    NormalizeAndPostprocessStep,
)

logger = logging.getLogger(__name__)


@dataclass
class InsertFixtureNodesTask(Task):
    id: str = "tasks.fixture_injector.insert_fixture_nodes"
    name: str = "insert_fixture_nodes"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        # Early validation: ensure module and nodes are present
        maybe_module = context.get("module")
        module: cst.Module | None = maybe_module if isinstance(maybe_module, cst.Module) else None
        nodes = context.get("fixture_nodes") or []
        if module is None or not isinstance(nodes, list) or not nodes:
            return TaskResult(delta=ContextDelta(values={"module": module}))

        # Prepare steps. run_steps will fold deltas back into a TaskResult
        steps: list[Step] = [
            FindInsertionIndexStep(),
            InsertNodesStep(),
            NormalizeAndPostprocessStep(),
        ]

        # Seed context with fixture_nodes so steps can access it
        working = dict(context)
        working["fixture_nodes"] = nodes
        return run_steps(
            stage_id=working.get("__stage_id__", "stages.fixture_injector"),
            task_id=self.id,
            task_name=self.name,
            steps=steps,
            context=working,
            resources=resources,
        )


__all__ = ["InsertFixtureNodesTask"]
