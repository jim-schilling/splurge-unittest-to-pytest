from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage


def _run_module(src: str) -> dict:
    module = cst.parse_module(src)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    return generator_stage({"module": module, "collector_output": out})


def test_avoid_module_level_name_collision() -> None:
    src = """
_some_global = 1

class T(unittest.TestCase):
    def setUp(self) -> None:
        self.x = 1

    def tearDown(self) -> None:
        self.x = None
"""
    res = _run_module(src)
    nodes = res["fixture_nodes"]
    node = next(n for n in nodes if n.name.value == "x")
    s = cst.Module(body=[node]).code
    # Should avoid colliding with existing _some_global or common _x_value
    assert "_x_value" in s or "_x_value_" in s
    # But should not equal a name that already exists at module level exactly
    assert "_some_global" in src
    assert "_some_global" not in s
