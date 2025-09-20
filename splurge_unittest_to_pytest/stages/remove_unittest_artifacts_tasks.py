"""CstTask for removing unittest artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from ..types import Task, TaskResult
from .steps import run_steps
from .steps_remove_unittest_artifacts import ParseRemoveUnittestStep, RemoveUnittestArtifactsStep

if TYPE_CHECKING:
    from ..types import Step


DOMAINS = ["stages", "helpers", "tasks"]


@dataclass
class RemoveUnittestArtifactsTask(Task):
    id: str = "tasks.helpers.remove_unittest_artifacts"
    name: str = "remove_unittest_artifacts"
    steps: Sequence["Step"] = ()

    def _ensure_steps(self) -> None:
        if not self.steps:
            self.steps = [ParseRemoveUnittestStep(), RemoveUnittestArtifactsStep()]

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        # Use the Step runner for clearer, testable behavior
        self._ensure_steps()
        return run_steps("stages.helpers", self.id, self.name, list(self.steps), context, resources)


__all__ = ["RemoveUnittestArtifactsTask"]
