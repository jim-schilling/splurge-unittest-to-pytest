from splurge_unittest_to_pytest.stages.events import EventBus, HookRegistry, RecordingObserver
from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.types import ContextDelta, StepResult


class DummyStep:
    id = "s1"
    name = "dummy1"

    def execute(self, ctx, resources):
        return StepResult(delta=ContextDelta(values={"k1": 1}))


class DummyStep2:
    id = "s2"
    name = "dummy2"

    def execute(self, ctx, resources):
        return StepResult(delta=ContextDelta(values={"k2": 2}))


def test_eventbus_and_hooks_invoked_in_order():
    import os

    # enable diagnostics so step-level events are emitted
    old = os.environ.get("SPLURGE_ENABLE_DIAGNOSTICS")
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"

    bus = EventBus()
    rec = RecordingObserver()
    # subscribe the recording observer to step/task lifecycle events
    from splurge_unittest_to_pytest.stages.events import StepCompleted, StepStarted, TaskCompleted, TaskStarted

    bus.subscribe(TaskStarted, rec)
    bus.subscribe(StepStarted, rec)
    bus.subscribe(StepCompleted, rec)
    bus.subscribe(TaskCompleted, rec)

    hooks = HookRegistry()
    order = []

    def before_task(stage_name, task_name, ctx):
        order.append("before_task")

    def before_step(task_name, step_name, ctx):
        order.append(f"before_step:{step_name}")

    def after_step(task_name, step_name, result):
        order.append(f"after_step:{step_name}")

    def after_task(stage_name, task_name, result):
        order.append("after_task")

    hooks.on("before_task", before_task)
    hooks.on("before_step", before_step)
    hooks.on("after_step", after_step)
    hooks.on("after_task", after_task)

    ctx = {"module": None, "__event_bus__": bus, "__hooks__": hooks, "__stage_id__": "stages.test"}
    steps = [DummyStep(), DummyStep2()]
    run_steps("stages.test", "tasks.test", "test", steps, ctx, resources=None)

    # restore env
    if old is None:
        del os.environ["SPLURGE_ENABLE_DIAGNOSTICS"]
    else:
        os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = old

    # Hooks must have been called in order: before_task ... after_task
    assert order[0] == "before_task"
    assert "before_step:dummy1" in order
    assert "after_step:dummy1" in order
    assert "before_step:dummy2" in order
    assert "after_step:dummy2" in order
    assert order[-1] == "after_task"

    # EventBus should have recorded the lifecycle events in the observer
    names = [type(e).__name__ for e in rec.events]
    assert "TaskStarted" in names
    assert "StepStarted" in names
    assert "StepCompleted" in names
    assert "TaskCompleted" in names
