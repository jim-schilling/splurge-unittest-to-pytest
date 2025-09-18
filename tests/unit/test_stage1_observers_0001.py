import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.stages import diagnostics


def test_manager_emits_stage_completed_and_diagnostics_writes(tmp_path, monkeypatch):
    # Enable diagnostics and force diagnostics dir to our tmp_path
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")

    def _fake_create_dir():
        return tmp_path

    monkeypatch.setattr(diagnostics, "create_diagnostics_dir", _fake_create_dir)

    def simple_stage(ctx):
        return {}

    mgr = StageManager([simple_stage])
    module = cst.parse_module("x = 0")
    mgr.run(module)

    # DiagnosticsObserver should have written 01_simple_stage.py
    files = {p.name for p in tmp_path.iterdir()}
    assert any(name.startswith("01_simple_stage.py") for name in files) or "01_simple_stage.py" in files
