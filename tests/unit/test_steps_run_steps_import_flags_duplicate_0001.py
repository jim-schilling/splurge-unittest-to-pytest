import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.types import ContextDelta, StepResult


class FakeStepPytestA:
    id = "fake.step.pytest.a"
    name = "fake_pytest_a"

    def execute(self, context, resources):
        return StepResult(delta=ContextDelta(values={"needs_pytest_import": True}))


class FakeStepPytestB:
    id = "fake.step.pytest.b"
    name = "fake_pytest_b"

    def execute(self, context, resources):
        return StepResult(delta=ContextDelta(values={"needs_pytest_import": True}))


def test_run_steps_dedups_pytest_flag():
    module = cst.parse_module("\n")
    context = {"module": module}
    steps = [FakeStepPytestA(), FakeStepPytestB()]

    res = run_steps(
        stage_id="test.stage", task_id="test.task", task_name="test", steps=steps, context=context, resources=None
    )

    assert res.errors == []
    delta_vals = res.delta.values
    # dedup/OR behavior: flag should be present and True
    assert delta_vals.get("needs_pytest_import") is True
