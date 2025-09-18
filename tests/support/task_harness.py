from __future__ import annotations

from typing import Any, Mapping

from splurge_unittest_to_pytest.types import Task, TaskResult


class TaskTestHarness:
    """Minimal harness to execute a Task with a given context.

    Returns the TaskResult; callers can assert on delta contents and errors.
    """

    def __init__(self, task: Task) -> None:
        self.task = task

    def run(self, context: Mapping[str, Any]) -> TaskResult:
        return self.task.execute(context, resources=None)
