from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages.import_injector_tasks import (
    DetectNeedsCstTask,
    InsertImportsCstTask,
)
from tests.support.task_harness import TaskTestHarness


def _module_from(code: str) -> cst.Module:
    return cst.parse_module(code)


def test_detect_needs_sets_pytest_flag_when_usage_present() -> None:
    mod = _module_from("""
def f():
    pytest.raises(ValueError)
""")
    ctx = {"module": mod, "__stage_id__": "stages.import_injector"}
    res = TaskTestHarness(DetectNeedsCstTask()).run(ctx)
    assert res.delta.values.get("needs_pytest_import") is True


def test_insert_imports_inserts_pytest_when_flag_true() -> None:
    mod = _module_from("""
def f():
    pass
""")
    ctx = {
        "module": mod,
        "needs_pytest_import": True,
        "__stage_id__": "stages.import_injector",
    }
    res = TaskTestHarness(InsertImportsCstTask()).run(ctx)
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    assert "import pytest" in new_mod.code
