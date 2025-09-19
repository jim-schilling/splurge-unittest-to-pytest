import libcst as cst

from splurge_unittest_to_pytest.stages.steps_fixtures_stage import CollectClassesStep, BuildTopLevelFnsStep
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.steps import run_steps


def test_collect_and_build_top_level_functions_simple():
    src = """
import unittest

class TestX(unittest.TestCase):
    def setUp(self):
        self.a = 1

    def test_one(self):
        assert self.a == 1
"""
    mod = cst.parse_module(src)
    collector = Collector()
    mod.visit(collector)
    out = collector.as_output()

    context = {"module": mod, "collector_output": out}
    res = run_steps("st", "t", "n", [CollectClassesStep(), BuildTopLevelFnsStep()], context, None)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # class should be removed and a top-level test function present
    assert any(isinstance(n, cst.FunctionDef) and n.name.value.startswith("test") for n in new_mod.body)


def test_build_top_level_handles_no_collector():
    # When collector missing, steps should be no-op and return original module
    src = "import unittest\n"
    mod = cst.parse_module(src)
    context = {"module": mod}
    res = run_steps("st", "t", "n", [CollectClassesStep(), BuildTopLevelFnsStep()], context, None)
    assert res.errors == []
    assert res.delta.values.get("module") is mod or res.delta.values.get("module") is None
