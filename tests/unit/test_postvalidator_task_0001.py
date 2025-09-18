from types import SimpleNamespace

from splurge_unittest_to_pytest.stages.postvalidator_tasks import ValidateModuleTask
from tests.support.task_harness import TaskTestHarness


def test_postvalidator_attaches_error_on_invalid_code():
    bad = SimpleNamespace(code="def x(:\n")
    res = TaskTestHarness(ValidateModuleTask()).run({"module": bad})
    assert "postvalidator_error" in res.delta.values
