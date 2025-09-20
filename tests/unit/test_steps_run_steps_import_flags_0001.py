import libcst as cst
from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.types import ContextDelta, StepResult


class FakeStepPytest:
    id = "fake.step.pytest"
    name = "fake_pytest"

    def execute(self, context, resources):
        # return a delta that requests pytest import
        return StepResult(delta=ContextDelta(values={"needs_pytest_import": True}))


class FakeStepRe:
    id = "fake.step.re"
    name = "fake_re"

    def execute(self, context, resources):
        # return a delta that requests re import
        return StepResult(delta=ContextDelta(values={"needs_re_import": True}))


def test_run_steps_merges_import_flags():
    module = cst.parse_module("\n")
    context = {"module": module}
    steps = [FakeStepPytest(), FakeStepRe()]

    res = run_steps(
        stage_id="test.stage", task_id="test.task", task_name="test", steps=steps, context=context, resources=None
    )

    assert res.errors == []
    delta_vals = res.delta.values
    assert delta_vals.get("needs_pytest_import") is True
    assert delta_vals.get("needs_re_import") is True
