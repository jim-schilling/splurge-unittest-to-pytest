from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.stages.collector import Collector


SAMPLE = """
class MyTests(unittest.TestCase):
    def setUp(self):
        self.x = 1

    def tearDown(self):
        self.x = None

    def test_one(self):
        assert self.x == 1
"""


def collector_stage(context: dict) -> dict:
    module: cst.Module = context["module"]
    visitor = Collector()
    module.visit(visitor)
    return {"collector_output": visitor.as_output()}


def test_stage_manager_runs_collector():
    module = cst.parse_module(SAMPLE)
    mgr = StageManager()
    mgr.register(collector_stage)
    ctx = mgr.run(module)
    assert "collector_output" in ctx
    co = ctx["collector_output"]
    assert 'MyTests' in co.classes
