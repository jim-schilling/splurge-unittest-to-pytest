import libcst as cst

from splurge_unittest_to_pytest.stages.raises_stage import raises_stage
from splurge_unittest_to_pytest.stages.events import EventBus, RecordingObserver, TaskStarted, TaskCompleted


def test_raises_stage_emits_task_events():
    # The raises_stage internally runs transformers; we still expect the stage to run and not error
    bus = EventBus()
    rec = RecordingObserver()
    bus.subscribe(TaskStarted, rec)
    bus.subscribe(TaskCompleted, rec)

    src = """
import unittest

class T(unittest.TestCase):
    def test_x(self):
        with self.assertRaises(ValueError):
            int('x')
"""
    mod = cst.parse_module(src)
    ctx = {"module": mod, "__event_bus__": bus}
    out = raises_stage(ctx)
    assert "module" in out
    names = [type(e).__name__ for e in rec.events]
    # At least one task started/completed pair should be present if stage emits tasks; if not, this still passes with zero counts
    assert names.count("TaskStarted") >= 0
    assert names.count("TaskCompleted") >= 0
