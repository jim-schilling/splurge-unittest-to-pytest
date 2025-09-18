import libcst as cst

from splurge_unittest_to_pytest.stages.import_injector_tasks import DetectNeedsCstTask, InsertImportsCstTask
from splurge_unittest_to_pytest.stages.events import EventBus, RecordingObserver, TaskStarted, TaskCompleted
from tests.support.task_harness import TaskTestHarness


def test_detect_needs_flags_from_module_text():
    module = cst.parse_module("""
import json

def f():
    import shutil
    return os.getenv('X') or sys.version
""")
    ctx = {"module": module}
    res = TaskTestHarness(DetectNeedsCstTask()).run(ctx)
    vals = res.delta.values
    # New behavior: only set pytest flag when detected or explicitly requested
    assert "needs_pytest_import" not in vals or vals.get("needs_pytest_import") is True
    assert vals.get("needs_shutil_import") is True
    assert vals.get("needs_os_import") is True
    assert vals.get("needs_sys_import") is True


def test_insert_imports_inserts_expected(tmp_path, monkeypatch):
    module = cst.parse_module("x = 1")
    ctx = {"module": module, "needs_pytest_import": True, "needs_os_import": True}
    res = TaskTestHarness(InsertImportsCstTask()).run(ctx)
    new_mod = res.delta.values["module"]
    code = new_mod.code
    assert "import pytest" in code
    assert "import os" in code


def test_per_task_events_emitted(monkeypatch):
    # Wire a bus into context and verify TaskStarted/TaskCompleted are emitted
    module = cst.parse_module("x = 1")
    bus = EventBus()
    rec = RecordingObserver()
    bus.subscribe(TaskStarted, rec)
    bus.subscribe(TaskCompleted, rec)

    # Simulate the stage body
    ctx = {"module": module, "__event_bus__": bus}
    from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage

    out = import_injector_stage(ctx)
    assert "module" in out
    names = [type(e).__name__ for e in rec.events]
    assert names.count("TaskStarted") >= 2
    assert names.count("TaskCompleted") >= 2
