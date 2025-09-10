from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage


def _run(src: str):
    module = cst.parse_module(src)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    return generator_stage({"module": module, "collector_output": out})


def test_literal_binding_and_cleanup():
    src = """
class T(unittest.TestCase):
    def setUp(self):
        self.flag = True

    def tearDown(self):
        if self.flag:
            self.flag = False
"""
    res = _run(src)
    nodes = res["fixture_nodes"]
    flag_node = next(n for n in nodes if n.name.value == "flag")
    s = cst.Module(body=[flag_node]).code
    # Even though flag had a literal, it should be bound and teardown should reference the local name
    assert "_flag_value" in s or "_flag_value_" in s
    assert "= False" in s
    assert "yield" in s


def test_del_self_attr_cleanup():
    src = """
class T(unittest.TestCase):
    def setUp(self):
        self.item = []

    def tearDown(self):
        del self.item
"""
    res = _run(src)
    nodes = res["fixture_nodes"]
    node = next(n for n in nodes if n.name.value == "item")
    s = cst.Module(body=[node]).code
    # del should be rewritten to del <local_name>
    assert "del " in s
    assert "self.item" not in s


def test_name_collision_uniqueness():
    src = """
class T(unittest.TestCase):
    def setUp(self):
        self.x = 1
        self.x = 2

    def tearDown(self):
        self.x = None
"""
    res = _run(src)
    nodes = res["fixture_nodes"]
    # Should create only one fixture named 'x' but local names should not collide
    xs = [n for n in nodes if n.name.value == "x"]
    assert len(xs) == 1
    s = cst.Module(body=[xs[0]]).code
    # local name should exist and be unique-looking
    assert "_x_value" in s
    assert "= None" in s
