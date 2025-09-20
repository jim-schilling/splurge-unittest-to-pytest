import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter_tasks import RewriteAssertionsTask
from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import (
    ParseAssertionsStep,
    TransformComparisonAssertionsStep,
    TransformRaisesAssertionsStep,
    EmitAssertionsStep,
)
from splurge_unittest_to_pytest.stages.steps import run_steps


def _module(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_rewriter_multistep_parity_minimal():
    src = """
def test_example():
    self.assertEqual(1, 1)
"""
    mod = _module(src)

    # Baseline: original Task
    task = RewriteAssertionsTask()
    res_task = task.execute({"module": mod}, resources=None)

    # Run via three Steps
    from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import (
        TransformComplexAssertionsStep,
    )

    steps = [
        ParseAssertionsStep(),
        TransformComparisonAssertionsStep(),
        TransformRaisesAssertionsStep(),
        TransformComplexAssertionsStep(),
        EmitAssertionsStep(),
    ]
    res_steps = run_steps(
        stage_id="s", task_id=task.id, task_name=task.name, steps=steps, context={"module": mod}, resources=None
    )

    mod_task = res_task.delta.values.get("module")
    mod_steps = res_steps.delta.values.get("module")
    assert isinstance(mod_task, cst.Module)
    assert isinstance(mod_steps, cst.Module)
    assert mod_task.code == mod_steps.code


def test_rewriter_task_execute_uses_steps_flag():
    src = """
def test_example():
    self.assertEqual(2, 2)
"""
    mod = _module(src)
    task = RewriteAssertionsTask()
    # Run the Task with the feature flag enabled
    res_flag = task.execute({"module": mod, "USE_STEPS_REWRITER": True}, resources=None)
    res_direct = task.execute({"module": mod}, resources=None)
    assert res_flag.delta.values.get("module").code == res_direct.delta.values.get("module").code


def test_rewriter_step_errors_stop():
    class ErrorStep:
        id = "steps.test.error"
        name = "error"

        def execute(self, context, resources):
            from splurge_unittest_to_pytest.types import StepResult, ContextDelta

            return StepResult(delta=ContextDelta(values={}), errors=[RuntimeError("boom")])

    # a later step that would mutate delta if executed
    class MutatingStep:
        id = "steps.test.mut"
        name = "mut"

        def execute(self, context, resources):
            from splurge_unittest_to_pytest.types import StepResult, ContextDelta

            return StepResult(delta=ContextDelta(values={"mutated": True}))

    steps = [ErrorStep(), MutatingStep()]
    res = run_steps(stage_id="s", task_id="t", task_name="t", steps=steps, context={}, resources=None)
    assert res.errors
    assert res.delta.values.get("mutated") is None
