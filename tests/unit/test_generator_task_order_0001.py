from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator_tasks import BuildFixtureSpecsTask, FinalizeGeneratorTask
from tests.support.task_harness import TaskTestHarness


def test_generator_task_ordering_and_delta_folding() -> None:
    src = """
class TestY:
    def setUp(self):
        self._x = 123
    def test_ok(self):
        assert self._x == 123
"""
    mod = cst.parse_module(src)
    wrapper = cst.MetadataWrapper(mod)
    v = Collector()
    wrapper.visit(v)
    out = v.as_output()
    base_ctx = {"module": mod, "collector_output": out, "__stage_id__": "stages.generator"}

    # Run build step/task
    build_res = TaskTestHarness(BuildFixtureSpecsTask()).run(base_ctx)
    # Merge delta into context, simulating manager behavior
    tmp_ctx = dict(base_ctx)
    tmp_ctx.update(build_res.delta.values)
    # Run finalize step/task with merged context
    fin_res = TaskTestHarness(FinalizeGeneratorTask()).run(tmp_ctx)

    # Ensure finalize used prior delta keys (e.g., gen_fixture_nodes) to produce final outputs
    assert "fixture_nodes" in fin_res.delta.values
    assert "fixture_specs" in fin_res.delta.values
    # When yield-style not required, needs_typing_names may be absent or empty; allow either
    needs_typing = fin_res.delta.values.get("needs_typing_names")
    assert needs_typing is None or isinstance(needs_typing, list)
