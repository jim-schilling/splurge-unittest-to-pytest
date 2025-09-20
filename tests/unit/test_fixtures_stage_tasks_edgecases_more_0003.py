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


def test_starred_assignment_into_attributes_is_idempotent():
    src = """
import unittest

class TestStarredAttr(unittest.TestCase):
    def setUp(self):
        self.x, *self.y = [1, 2, 3, 4]

    def test_values(self):
        assert self.x == 1
        assert self.y == [2, 3, 4]
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_chained_attribute_targets_are_idempotent():
    src = """
import unittest

class Node:
    def __init__(self):
        self.value = None

class TestChainedAttr(unittest.TestCase):
    def setUp(self):
        a = Node()
        a.b = Node()
        a.b.c = 5
        self.a = a

    def test_values(self):
        assert self.a.b.c == 5
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def make_complex_return():
    return {"a": (1, [2, 3], {"x": 9}), "b": [4, 5]}


def test_destructuring_from_complex_function_return_is_idempotent():
    src = """
import unittest

def make_complex_return():
    return {'a': (1, [2, 3], {'x': 9}), 'b': [4, 5]}

class TestDestructureComplex(unittest.TestCase):
    def setUp(self):
        d = make_complex_return()
        a1, (a2, *a3), a4 = (d['a'][0], d['a'][1], d['a'][2]['x'])
        self.a1 = a1
        self.a2 = a2
        self.a3 = a3
        self.a4 = a4

    def test_values(self):
        assert self.a1 == 1
        assert self.a2 == 2
        assert self.a3 == [3]
        assert self.a4 == 9
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_assignment_to_descriptor_property_is_idempotent():
    src = """
import unittest

class Desc:
    def __set__(self, instance, value):
        instance._val = value

class Owner:
    desc = Desc()

class TestDescriptor(unittest.TestCase):
    def setUp(self):
        o = Owner()
        o.desc = 42
        self.o = o

    def test_values(self):
        assert self.o._val == 42
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code
