from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages.collector import Collector, CollectorOutput
from splurge_unittest_to_pytest.stages.generator_tasks import BuildFixtureSpecsTask
from tests.support.task_harness import TaskTestHarness


def test_build_specs_step_produces_fixture_nodes_smoke() -> None:
    src = """
class TestX:
    def setUp(self):
        self._resource = 1
    def test_it(self):
        assert self._resource == 1
"""
    mod = cst.parse_module(src)
    wrapper = cst.MetadataWrapper(mod)
    v = Collector()
    wrapper.visit(v)
    out: CollectorOutput = v.as_output()
    ctx = {"module": mod, "collector_output": out, "__stage_id__": "stages.generator"}
    res = TaskTestHarness(BuildFixtureSpecsTask()).run(ctx)
    nodes = res.delta.values.get("gen_fixture_nodes")
    assert isinstance(nodes, list)
    # Ensure at least one fixture was produced
    assert any(isinstance(n, cst.FunctionDef) for n in nodes)
