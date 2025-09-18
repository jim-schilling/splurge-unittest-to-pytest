import libcst as cst

from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes_tasks import ApplyDecoratorAndMockFixesTask
from tests.support.task_harness import TaskTestHarness


def test_skip_if_converted_to_pytest_mark_skipif():
    src = """
import unittest

@unittest.skipIf(True, 'because')
def test_x():
    pass
"""
    mod = cst.parse_module(src)
    res = TaskTestHarness(ApplyDecoratorAndMockFixesTask()).run({"module": mod})
    code = res.delta.values["module"].code
    assert (
        "@pytest.mark.skipif(True, reason='because')" in code or '@pytest.mark.skipif(True, reason="because")' in code
    )
