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


def helper_return_nested():
    return (1, (2, 3), [4, 5])


def test_nested_tuple_unpacking_and_starred_assignment_is_idempotent():
    src = """
import unittest

class TestNestedUnpack(unittest.TestCase):
    def setUp(self):
        a, (b, c), [d, *e] = helper_return_nested()
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e

    def test_values(self):
        assert self.a == 1
        assert self.b == 2
        assert self.c == 3
        assert self.d == 4
        assert self.e == [5]
"""
    # simpler: include helper in src
    src = """
import unittest

def helper_return_nested():
    return (1, (2, 3), [4, 5])

class TestNestedUnpack(unittest.TestCase):
    def setUp(self):
        a, (b, c), [d, *e] = helper_return_nested()
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e

    def test_values(self):
        assert self.a == 1
        assert self.b == 2
        assert self.c == 3
        assert self.d == 4
        assert self.e == [5]
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_destructuring_from_function_return_is_idempotent():
    src = """
import unittest

def make_values():
    return (100, 200)

class TestDestructure(unittest.TestCase):
    def setUp(self):
        x, y = make_values()
        self.x = x
        self.y = y

    def test_values(self):
        assert self.x == 100
        assert self.y == 200
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_complex_attribute_assignments_in_setup_are_idempotent():
    src = """
import unittest

class Nested:
    def __init__(self):
        self.value = 0

class TestComplexAttr(unittest.TestCase):
    def setUp(self):
        self.n = Nested()
        self.n.value, self.other = (7, {'k': 'v'})

    def test_values(self):
        assert self.n.value == 7
        assert self.other == {'k': 'v'}
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code
