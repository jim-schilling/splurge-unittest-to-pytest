from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.types import ContextDelta, Step, StepResult, TaskResult


@dataclass
class DummyStep(Step):
    id: str = "dummy"
    name: str = "dummy"

    def __init__(self, delta: Mapping[str, Any]):
        self._delta = dict(delta)

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        return StepResult(delta=ContextDelta(values=self._delta))


@dataclass
class ErrorStep(Step):
    id: str = "err"
    name: str = "err"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        return StepResult(delta=ContextDelta(values={}), errors=[RuntimeError("step failed")])


@dataclass
class RaiseStep(Step):
    id: str = "raise"
    name: str = "raise"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        raise ValueError("boom")


def test_run_steps_happy_path():
    steps = [DummyStep({"a": 1}), DummyStep({"b": 2})]
    res: TaskResult = run_steps("stage.x", "task.x", "task_x", steps, {"module": cst.parse_module("")}, None)
    assert not res.errors
    assert res.delta.values["a"] == 1
    assert res.delta.values["b"] == 2


def test_run_steps_handles_step_errors():
    steps = [DummyStep({"a": 1}), ErrorStep(), DummyStep({"c": 3})]
    res = run_steps("stage.x", "task.x", "task_x", steps, {"module": cst.parse_module("")}, None)
    assert res.errors
    assert isinstance(res.errors[0], RuntimeError)
    # Ensure subsequent steps were not run
    assert "c" not in res.delta.values


def test_run_steps_handles_exceptions():
    steps = [DummyStep({"a": 1}), RaiseStep(), DummyStep({"c": 3})]
    res = run_steps("stage.x", "task.x", "task_x", steps, {"module": cst.parse_module("")}, None)
    assert res.errors
    assert isinstance(res.errors[0], ValueError)
    assert "c" not in res.delta.values


def test_transient_keys_not_exposed():
    steps = [DummyStep({"__tmp_step__x": 1, "a": 2})]
    res = run_steps("stage.x", "task.x", "task_x", steps, {"module": cst.parse_module("")}, None)
    assert "a" in res.delta.values
    assert not any(k.startswith("__tmp_step__") for k in res.delta.values)
