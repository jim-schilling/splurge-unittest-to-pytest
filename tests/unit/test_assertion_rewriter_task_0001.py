import libcst as cst

from splurge_unittest_to_pytest.stages.assertion_rewriter_tasks import RewriteAssertionsTask
from tests.support.task_harness import TaskTestHarness


def test_rewrite_assert_equal_to_assert_statement():
    src = """
import unittest

class T(unittest.TestCase):
    def test_x(self):
        self.assertEqual(a, b)
"""
    mod = cst.parse_module(src)
    res = TaskTestHarness(RewriteAssertionsTask()).run({"module": mod})
    new_mod = res.delta.values.get("module")
    code = new_mod.code
    assert "assert a == b" in code
