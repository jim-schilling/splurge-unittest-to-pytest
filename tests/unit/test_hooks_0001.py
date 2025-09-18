import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


def test_hooks_ordering_and_error_isolation():
    calls: list[str] = []

    def on_before_stage(stage_name: str, context: dict):
        calls.append(f"before_stage:{stage_name}")

    def on_after_stage(stage_name: str, result: dict):
        calls.append(f"after_stage:{stage_name}")

    def on_before_task(stage_name: str, task_name: str, context: dict):
        calls.append(f"before_task:{stage_name}:{task_name}")

    def on_after_task(stage_name: str, task_name: str, result: dict):
        calls.append(f"after_task:{stage_name}:{task_name}")

    def on_before_task_raises(stage_name: str, task_name: str, context: dict):
        # should be isolated and not break other hooks or stage execution
        raise RuntimeError("hook error")

    mgr = StageManager([import_injector_stage])
    # access internal hook registry for unit testing
    hooks = getattr(mgr, "_hooks")
    hooks.on("before_stage", on_before_stage)
    hooks.on("after_stage", on_after_stage)
    hooks.on("before_task", on_before_task)
    hooks.on("before_task", on_before_task_raises)
    hooks.on("after_task", on_after_task)

    module = cst.parse_module("x = 0")
    mgr.run(module)

    # Expect one before_stage and one after_stage
    assert calls[0] == "before_stage:import_injector_stage"
    assert calls[-1] == "after_stage:import_injector_stage"

    # Expect before/after task pairs for two tasks: detect_needs, insert_imports
    before_tasks = [c for c in calls if c.startswith("before_task:")]
    after_tasks = [c for c in calls if c.startswith("after_task:")]
    assert len(before_tasks) >= 2
    assert len(after_tasks) >= 2
    # Order: before_stage -> before_task (detect) ... after_task (detect) ... before_task (insert) ... after_task (insert) ... -> after_stage
    assert "before_task:stages.import_injector:detect_needs" in calls
    assert "after_task:stages.import_injector:detect_needs" in calls
    assert "before_task:stages.import_injector:insert_imports" in calls
    assert "after_task:stages.import_injector:insert_imports" in calls
