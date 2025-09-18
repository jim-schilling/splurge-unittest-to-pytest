import libcst as cst

from splurge_unittest_to_pytest.stages.remove_unittest_artifacts_tasks import RemoveUnittestArtifactsTask
from tests.support.task_harness import TaskTestHarness


def test_removes_unittest_import_and_main_guard():
    src = """
import unittest

if __name__ == '__main__':
    unittest.main()
"""
    mod = cst.parse_module(src)
    res = TaskTestHarness(RemoveUnittestArtifactsTask()).run({"module": mod})
    code = res.delta.values["module"].code
    assert "import unittest" not in code
    assert "__main__" not in code
