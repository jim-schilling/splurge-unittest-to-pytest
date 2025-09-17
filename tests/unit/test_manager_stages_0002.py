import shutil
import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager

DOMAINS = ["manager", "stages"]


def _cleanup_mgr_dir(mgr: StageManager) -> None:
    d = getattr(mgr, "_diagnostics_dir", None)
    if d is None:
        return
    try:
        shutil.rmtree(d)
    except Exception:
        # best-effort cleanup
        pass


def test_diagnostics_marker_and_dir_created(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    try:
        assert mgr._diagnostics_dir is not None
        # marker file is created inside the diagnostics dir
        marker_files = [p for p in mgr._diagnostics_dir.iterdir() if p.name.startswith("splurge-diagnostics-")]
        assert marker_files, "marker file missing"
        marker = marker_files[0]
        content = marker.read_text(encoding="utf-8")
        assert content == str(mgr._diagnostics_dir.resolve())
    finally:
        _cleanup_mgr_dir(mgr)


def test_dump_initial_and_final_create_files(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    try:
        module = cst.parse_module("x = 1\n")
        mgr.dump_initial(module)
        mgr.dump_final(module)
        assert (mgr._diagnostics_dir / "00_initial_input.py").exists()
        assert (mgr._diagnostics_dir / "99_final_output.py").exists()
    finally:
        _cleanup_mgr_dir(mgr)


def test_no_diagnostics_when_disabled(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    try:
        module = cst.parse_module("x = 1\n")
        mgr.dump_initial(module)
        mgr.dump_final(module)
        assert mgr._diagnostics_dir is None
    finally:
        _cleanup_mgr_dir(mgr)


def test_register_and_run_writes_stage_snapshot(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    try:

        def my_stage(ctx: dict) -> dict:
            # simple stage that returns a small dict
            ctx["stage_marker"] = True
            return {"processed": True}

        mgr.register(my_stage)
        module = cst.parse_module("y = 2\n")
        ctx = mgr.run(module)
        assert ctx.get("processed") is True or ctx.get("stage_marker") is True
        files = list(mgr._diagnostics_dir.iterdir())
        assert any(p.name.endswith("_my_stage.py") for p in files)
    finally:
        _cleanup_mgr_dir(mgr)
