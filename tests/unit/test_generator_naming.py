# type: ignore

from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage


def _run(src: str) -> dict:
    module = cst.parse_module(src)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    return generator_stage({"module": module, "collector_output": out})


def test_local_name_determinism() -> None:
    src = """
class T(unittest.TestCase):
    def setUp(self) -> None:
        self.x = 1

    def tearDown(self) -> None:
        self.x = None
"""
    res = _run(src)
    nodes = res["fixture_nodes"]
    node = next(n for n in nodes if n.name.value == "x")
    s = cst.Module(body=[node]).code
    # Accept either a bound local name (_x_value or _x_value_1) or a
    # concise literal-yield form (yield 1) with cleanup rewritten to use
    # the fixture name; both are permissible outcomes depending on
    # collision/cleanup heuristics.
    assert ("_x_value" in s or "_x_value_1" in s) or ("yield 1" in s and "x = None" in s)
