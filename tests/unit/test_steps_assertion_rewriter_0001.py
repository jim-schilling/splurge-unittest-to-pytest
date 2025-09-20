import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter_tasks import RewriteAssertionsTask
from splurge_unittest_to_pytest.stages.steps_assertion_rewriter import RunAssertionRewriterStep
from splurge_unittest_to_pytest.stages.steps import run_steps


def _module(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_rewriter_step_parity_minimal():
    src = """
def test_example():
    self.assertEqual(1, 1)
"""
    mod = _module(src)

    # Baseline: original Task
    task = RewriteAssertionsTask()
    res_task = task.execute({"module": mod}, resources=None)

    # Run via Step and run_steps
    step = RunAssertionRewriterStep()
    task_res = run_steps(
        stage_id="s", task_id=task.id, task_name=task.name, steps=[step], context={"module": mod}, resources=None
    )

    # Compare that module nodes string-wise to avoid CST object identity issues
    mod_task = res_task.delta.values.get("module")
    mod_step = task_res.delta.values.get("module")
    assert isinstance(mod_task, cst.Module)
    assert isinstance(mod_step, cst.Module)
    assert mod_task.code == mod_step.code
