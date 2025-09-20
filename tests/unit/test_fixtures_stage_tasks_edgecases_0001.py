import libcst as cst

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.fixtures_stage_tasks import BuildTopLevelTestsTask


def run_task_on_src(src: str):
    mod = cst.parse_module(src)
    collector = Collector()
    mod.visit(collector)
    out = collector.as_output()
    ctx = {"module": mod, "collector_output": out}
    task = BuildTopLevelTestsTask()
    return task.execute(ctx, resources=None)


def test_class_without_setup_is_idempotent():
    src = """
import unittest

class TestNoSetup(unittest.TestCase):
    def test_a(self):
        assert 1 == 1
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # Running again should not change the module
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_synthetic_functiontestcase_handled_and_idempotent():
    src = """
import unittest

def helper():
    return 1

test_case = unittest.FunctionTestCase(helper, setUp=lambda: None)
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # Run again on generated module (idempotency)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code
