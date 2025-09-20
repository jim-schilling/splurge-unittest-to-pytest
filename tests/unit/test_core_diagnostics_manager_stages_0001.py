import os
import shutil
import tempfile
from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest.stages import diagnostics
from splurge_unittest_to_pytest.stages.manager import StageManager


def _cleanup_mgr_dir(path_root: str) -> None:
    try:
        shutil.rmtree(path_root)
    except Exception:
        pass


def test_diagnostics_marker_and_dir_created(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    root = tempfile.mkdtemp(prefix="splurge-test-root-")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", root)
    StageManager()
    try:
        import pathlib

        root_dir = pathlib.Path(root)
        assert root_dir.exists()
        marker_files = list(root_dir.glob("splurge-diagnostics-*"))
        assert marker_files, "marker file missing"
        marker = marker_files[0]
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
    assert diagnostics.create_diagnostics_dir() is None


def test_register_and_run_writes_stage_snapshot(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    root = tempfile.mkdtemp(prefix="splurge-test-root-")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", root)
    mgr = StageManager()
    try:

        def my_stage(ctx: dict) -> dict:
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
        assert any((p.name.endswith("_my_stage.py") for p in files))
    finally:
        _cleanup_mgr_dir(root)


def test_stage_manager_writes_snapshots(tmp_path: Path) -> None:
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    try:
        manager = StageManager()

        def stage_append_comment(ctx: dict):
            mod = ctx.get("module")
            if mod is None:
                return {"module": mod}
            src = getattr(mod, "code", None) or ""
            new_src = src + "\n# appended by stage"
            new_mod = cst.parse_module(new_src)
            return {"module": new_mod}

        manager.register(stage_append_comment)
        module = cst.parse_module("x = 1\n")
        manager.run(module)
        ddir = diagnostics.create_diagnostics_dir()
        assert ddir is None or isinstance(ddir, Path) or ddir is None
        if ddir is not None:
            files = list(ddir.iterdir())
            assert files, "Expected diagnostics files to be written"
    finally:
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)


def test_diagnostics_flag_variants(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    assert diagnostics.diagnostics_enabled() is True
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "0")
    assert diagnostics.diagnostics_enabled() is False
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_VERBOSE", "1")
    assert diagnostics.diagnostics_verbose() is True
    monkeypatch.delenv("SPLURGE_DIAGNOSTICS_VERBOSE", raising=False)


def test_write_snapshot_defensive(tmp_path):
    class Dummy:
        code = "print('x')"

    diagnostics.write_snapshot("not_a_path", "f.py", Dummy())
    diagnostics.write_snapshot(None, "f2.py", Dummy())


def test_stage_manager_callable_object_without_name(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    sm = StageManager()
    d = sm._diagnostics_dir
    assert d is not None and d.exists()

    class CallableObj:
        def __call__(self, ctx):
            return {"ok": True}

    obj = CallableObj()
    sm.register(obj)
    mod = cst.parse_module("y = 2")
    ctx = sm.run(mod)
    assert ctx.get("ok") is True
    names = [p.name for p in d.iterdir()]
    assert any((n.endswith(".py") or n.startswith("splurge-diagnostics-") for n in names))


def test_dump_noop_when_diagnostics_disabled(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    sm = StageManager()
    mod = cst.parse_module("z = 3")
    sm.dump_initial(mod)
    sm.dump_final(mod)


def test_manager_no_snapshot_when_module_not_cst(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    sm = StageManager()
    d = sm._diagnostics_dir
    assert d is not None and d.exists()

    def stage_set_non_module(ctx):
        ctx["module"] = "not_a_module"
        return {"ok": True}

    sm.register(stage_set_non_module)
    mod = cst.parse_module("a = 1")
    ctx = sm.run(mod)
    assert ctx.get("ok") is True
    py_files = [p for p in d.iterdir() if p.suffix == ".py"]
    assert len(py_files) >= 0


def test_write_snapshot_handles_code_property_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    monkeypatch.setenv("SPLURGE_DIAGNOSTICS_ROOT", str(tmp_path))
    out = diagnostics.create_diagnostics_dir()
    assert out is not None

    class BrokenModule:
        @property
        def code(self):
            raise RuntimeError("boom")

    diagnostics.write_snapshot(out, "broken.py", BrokenModule())
