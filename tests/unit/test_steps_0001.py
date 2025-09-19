from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.types import StepResult, ContextDelta


@dataclass
class _AddKeyStep:
    id: str = "steps.test.add_key"
    name: str = "add_key"
    key: str = "a"
    value: Any = 1

    def execute(self, ctx: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        # Ensure we do not mutate input
        assert self.key not in ctx
        return StepResult(delta=ContextDelta(values={self.key: self.value}))


@dataclass
class _TmpOnlyStep:
    id: str = "steps.test.tmp_only"
    name: str = "tmp_only"

    def execute(self, ctx: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        # Return a temporary key that should be filtered out by run_steps
        return StepResult(delta=ContextDelta(values={"__tmp_step__": {"k": 1}}))


def test_run_steps_merges_deltas_and_preserves_purity() -> None:
    context: dict[str, Any] = {"__stage_id__": "stages.test"}
    result = run_steps("stages.test", "tasks.test", "test_task", [_AddKeyStep()], context, resources=None)
    assert result.errors == []
    assert result.delta.values == {"a": 1}
    # original context not mutated
    assert "a" not in context


def test_run_steps_filters_tmp_keys() -> None:
    context: dict[str, Any] = {"__stage_id__": "stages.test"}
    result = run_steps(
        "stages.test",
        "tasks.test",
        "test_task",
        [_TmpOnlyStep(), _AddKeyStep(key="b", value=2)],
        context,
        resources=None,
    )
    assert result.errors == []
    assert result.delta.values == {"b": 2}
