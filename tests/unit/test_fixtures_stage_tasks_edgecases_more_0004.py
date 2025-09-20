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


def test_descriptor_with_set_name_and_property_is_idempotent():
    src = """
import unittest

class Prop:
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        instance._vals = getattr(instance, '_vals', {})
        instance._vals[self.name] = value

class Owner:
    val = Prop()

class TestProp(unittest.TestCase):
    def setUp(self):
        o = Owner()
        o.val = 7
        self.o = o

    def test_values(self):
        assert self.o._vals['val'] == 7
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_destructuring_from_generator_expression_with_starred_is_idempotent():
    src = """
import unittest

class TestGenDestructure(unittest.TestCase):
    def setUp(self):
        a, *b = (i for i in [20, 21, 22, 23])
        self.a = a
        self.b = b

    def test_values(self):
        assert self.a == 20
        assert self.b == [21, 22, 23]
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_nested_destructuring_from_generator_function_is_idempotent():
    src = """
import unittest

def gen():
    yield 1
    yield (2, 3, 4)

class TestNestedGen(unittest.TestCase):
    def setUp(self):
        a, (b, *c) = gen()
        self.a = a
        self.b = b
        self.c = c

    def test_values(self):
        assert self.a == 1
        assert self.b == 2
        assert self.c == [3, 4]
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code
