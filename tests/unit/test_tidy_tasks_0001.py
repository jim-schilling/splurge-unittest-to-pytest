import libcst as cst

from splurge_unittest_to_pytest.stages.tidy_tasks import EnsureSelfParamTask, NormalizeSpacingTask
from tests.support.task_harness import TaskTestHarness


def test_normalize_spacing_inserts_two_blank_lines():
    src = """
def a():
    pass
def b():
    pass
"""
    mod = cst.parse_module(src)
    res = TaskTestHarness(NormalizeSpacingTask()).run({"module": mod})
    code = res.delta.values["module"].code
    assert "\n\n\ndef b(" in code or "\n\n\nclass" in code


def test_ensure_self_param_adds_self_to_test_methods_in_classes():
    src = """
class T:
    def test_x():
        pass
"""
    mod = cst.parse_module(src)
    res = TaskTestHarness(EnsureSelfParamTask()).run({"module": mod})
    code = res.delta.values["module"].code
    assert "def test_x(self):" in code
