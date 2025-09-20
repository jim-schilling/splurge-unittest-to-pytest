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


def test_setup_with_multiple_assignments_and_tuple_unpacking_is_idempotent():
    src = """
import unittest

class TestMultiSetup(unittest.TestCase):
    def setUp(self):
        # chained assignment
        self.a = self.b = 1
        # tuple unpacking
        self.c, self.d = (3, 4)

    def test_values(self):
        assert self.a == 1
        assert self.b == 1
        assert self.c == 3
        assert self.d == 4
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # Running again should not change the module
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_tuple_unpacking_in_setup_is_idempotent():
    src = """
import unittest

class TestTupleSetup(unittest.TestCase):
    def setUp(self):
        x, y = (10, 20)
        self.x, self.y = x, y

    def test_values(self):
        assert self.x == 10
        assert self.y == 20
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code


def test_private_fixture_names_preserved_and_idempotent():
    src = """
import unittest

class TestPrivateFixture(unittest.TestCase):
    def _helper(self):
        self._secret = 99

    def setUp(self):
        # call a private helper that sets a private attribute
        self._helper()

    def test_secret(self):
        assert self._secret == 99
"""
    res = run_task_on_src(src)
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    res2 = run_task_on_src(new_mod.code)
    assert res2.errors == []
    assert res2.delta.values.get("module").code == new_mod.code
