import libcst as cst

from splurge_unittest_to_pytest.stages.events import RecordingObserver, StageCompleted, StageStarted
from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_stage_started_completed_include_version(monkeypatch):
    # Attach a recorder to observe StageStarted/StageCompleted
    mgr = StageManager([import_injector_stage])
    rec = RecordingObserver()
    # direct subscription to manager's internal bus
    bus = getattr(mgr, "_event_bus")
    bus.subscribe(StageStarted, rec)
    bus.subscribe(StageCompleted, rec)

    module = cst.parse_module("x = 0")
    mgr.run(module)

    start_events = [e for e in rec.events if type(e).__name__ == "StageStarted"]
    comp_events = [e for e in rec.events if type(e).__name__ == "StageCompleted"]
    assert len(start_events) >= 1
    assert len(comp_events) >= 1
    # versions should be present and be strings
    assert isinstance(getattr(start_events[0], "version", None), str)
    assert isinstance(getattr(comp_events[0], "version", None), str)
