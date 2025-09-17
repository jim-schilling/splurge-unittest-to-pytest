import shutil
import tempfile
import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.stages import diagnostics

DOMAINS = ["manager", "stages"]


def _cleanup_mgr_dir(path_root: str) -> None:
    try:
        shutil.rmtree(path_root)
    except Exception:
        # best-effort cleanup
        pass


def test_diagnostics_marker_and_dir_created(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    # create an existing temporary root so the diagnostics helper can create
    # its per-run directory under it
    root = tempfile.mkdtemp(prefix="splurge-test-root-")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", root)
    # Construct manager for its side-effects (no need to keep reference)
    StageManager()
    try:
        # discover created diagnostics dir under the provided root
        import pathlib

        root_dir = pathlib.Path(root)
        assert root_dir.exists()
        marker_files = list(root_dir.glob("splurge-diagnostics-*"))
        assert marker_files, "marker file missing"
        marker = marker_files[0]
        # ensure marker file exists (do not attempt to read contents; the
        # helper may create the file with restrictive perms in some envs)
        assert marker.exists()
    finally:
        _cleanup_mgr_dir(root)


def test_dump_initial_and_final_create_files(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    root = tempfile.mkdtemp(prefix="splurge-test-root-")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", root)
    mgr = StageManager()
    try:
        module = cst.parse_module("x = 1\n")
        mgr.dump_initial(module)
        mgr.dump_final(module)
        import pathlib

        root_dir = pathlib.Path(root)
        # find the created diagnostics dir
        created_dirs = [p for p in root_dir.iterdir() if p.name.startswith("splurge-diagnostics-")]
        assert created_dirs, "diagnostics dir not created"
        diag = created_dirs[0]
        assert (diag / "00_initial_input.py").exists()
        assert (diag / "99_final_output.py").exists()
    finally:
        _cleanup_mgr_dir(root)


def test_no_diagnostics_when_disabled(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    module = cst.parse_module("x = 1\n")
    mgr.dump_initial(module)
    mgr.dump_final(module)
    # diagnostics_disabled -> create_diagnostics_dir public helper should return None
    assert diagnostics.create_diagnostics_dir() is None


def test_register_and_run_writes_stage_snapshot(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    root = tempfile.mkdtemp(prefix="splurge-test-root-")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", root)
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
        import pathlib

        root_dir = pathlib.Path(root)
        created_dirs = [p for p in root_dir.iterdir() if p.name.startswith("splurge-diagnostics-")]
        assert created_dirs, "diagnostics dir not created"
        diag = created_dirs[0]
        files = list(diag.iterdir())
        assert any(p.name.endswith("_my_stage.py") for p in files)
    finally:
        _cleanup_mgr_dir(root)
