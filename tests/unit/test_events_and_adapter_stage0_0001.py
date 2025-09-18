import libcst as cst

from splurge_unittest_to_pytest.stages.events import (
    EventBus,
    RecordingObserver,
    PipelineStarted,
    PipelineCompleted,
    DiagnosticsObserver,
)
from splurge_unittest_to_pytest.stages.adapters import CallableStage


def test_event_bus_records_start_and_completion():
    bus = EventBus()
    recorder = RecordingObserver()
    bus.subscribe(PipelineStarted, recorder)
    bus.subscribe(PipelineCompleted, recorder)

    bus.publish(PipelineStarted("run-1"))
    bus.publish(PipelineCompleted("run-1"))

    assert any(type(e).__name__ == "PipelineStarted" for e in recorder.events)
    assert any(type(e).__name__ == "PipelineCompleted" for e in recorder.events)


def test_callable_stage_executes_and_returns_delta():
    def legacy_stage(ctx: dict):
        ctx = dict(ctx)
        ctx["module"] = cst.parse_module("x = 1")
        ctx["needs_pytest_import"] = True
        return ctx

    stage = CallableStage(id="legacy", version="1", name="legacy_stage", _fn=legacy_stage)
    result = stage.execute({"module": cst.parse_module("x = 0")}, resources=None)
    assert isinstance(result.delta.values, dict)
    assert result.delta.values.get("needs_pytest_import") is True


def test_diagnostics_observer_writes_snapshot(tmp_path, monkeypatch):
    # Enable diagnostics and verify observer writes a file name with index and stage name
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    from splurge_unittest_to_pytest.stages.events import StageCompleted

    module = cst.parse_module("x = 1")
    obs = DiagnosticsObserver(tmp_path)
    # Include version field per updated StageCompleted signature
    obs(StageCompleted(run_id="r1", stage_id="s1", stage_name="import_injector", index=3, module=module, version="1"))
    files = {p.name for p in tmp_path.iterdir()}
    assert "03_import_injector.py" in files
