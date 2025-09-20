import libcst as cst

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.fixtures_stage_tasks import BuildTopLevelTestsTask


def make_sample_module():
    src = """
import unittest

class TestX(unittest.TestCase):
    def setUp(self):
        self.a = 1

    def test_one(self):
        assert self.a == 1
"""
    return cst.parse_module(src)


def test_build_top_level_task_delta_and_idempotency():
    mod = make_sample_module()
    collector = Collector()
    mod.visit(collector)
    out = collector.as_output()

    ctx = {"module": mod, "collector_output": out}
    task = BuildTopLevelTestsTask()

    # Execute the task once and assert it produced a module delta
    res = task.execute(ctx, resources=None)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # Ensure top-level test functions were emitted
    assert any(isinstance(n, cst.FunctionDef) and n.name.value.startswith("test") for n in new_mod.body)

    # Run the task again on the transformed module: should be idempotent
    ctx2 = {"module": new_mod, "collector_output": out}
    res2 = task.execute(ctx2, resources=None)
    assert res2.errors == []
    new_mod2 = res2.delta.values.get("module")
    # The module should be unchanged by a second run (idempotent)
    assert isinstance(new_mod2, cst.Module)
    assert new_mod2.code == new_mod.code
