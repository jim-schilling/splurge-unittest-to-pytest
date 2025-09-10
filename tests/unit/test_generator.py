from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage

SAMPLE = """
class MyTests(unittest.TestCase):
    def setUp(self):
        self.count = 5
        self.name = 'bob'

    def tearDown(self):
        if self.count is not None:
            self.count = None

    def test_one(self):
        assert self.count == 5
"""


def test_generator_creates_fixture_nodes():
    module = cst.parse_module(SAMPLE)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    ctx = {"module": module, "collector_output": out}
    result = generator_stage(ctx)
    specs = result.get("fixture_specs", {})
    nodes = result.get("fixture_nodes", [])
    assert "count" in specs
    assert "name" in specs
    # expect fixture nodes for 2 fixtures
    assert len(nodes) >= 2
    # fixture node names should match spec names
    node_names = {n.name.value for n in nodes}
    assert "count" in node_names
    assert "name" in node_names
    # find the count fixture node and verify it yields and contains cleanup
    count_node = next(n for n in nodes if n.name.value == "count")
    src = cst.Module(body=[count_node]).code
    assert "yield" in src
    # teardown should have been preserved (assignment to None)
    assert "= None" in src
