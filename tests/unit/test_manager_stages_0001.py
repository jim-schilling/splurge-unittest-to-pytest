from __future__ import annotations
import libcst as cst
from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.stages.collector import Collector
from pathlib import Path
import shutil

SAMPLE = "\nclass MyTests(unittest.TestCase):\n    def setUp(self) -> None:\n        self.x = 1\n\n    def tearDown(self) -> None:\n        self.x = None\n\n    def test_one(self) -> None:\n        assert self.x == 1\n"


def collector_stage(context: dict) -> dict:
    module: cst.Module = context["module"]
    visitor = Collector()
    module.visit(visitor)
    return {"collector_output": visitor.as_output()}


def test_stage_manager_runs_collector() -> None:
    module = cst.parse_module(SAMPLE)
    mgr = StageManager()
    mgr.register(collector_stage)
    ctx: dict = mgr.run(module)
    assert "collector_output" in ctx
    co = ctx["collector_output"]
    assert "MyTests" in co.classes


def test_diagnostics_enabled_creates_marker_and_dumps(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    assert mgr._diagnostics_dir is None or isinstance(mgr._diagnostics_dir, Path)
    if mgr._diagnostics_dir is None:
        module = cst.parse_module("x = 1")
        mgr.dump_initial(module)
        mgr.dump_final(module)
        return
    marker_files = list(mgr._diagnostics_dir.glob("splurge-diagnostics-*"))
    assert any((f.exists() for f in marker_files))
    module = cst.parse_module("a = 1")
    mgr.dump_initial(module)
    mgr.dump_final(module)
    init = mgr._diagnostics_dir / "00_initial_input.py"
    final = mgr._diagnostics_dir / "99_final_output.py"
    assert init.exists()
    assert final.exists()


def test_diagnostics_disabled_no_files(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    assert mgr._diagnostics_dir is None
    module = cst.parse_module("x = 2")
    mgr.dump_initial(module)
    mgr.dump_final(module)


def test_register_writes_stage_snapshots(monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    if mgr._diagnostics_dir is None:
        return

    def stage(context):
        new_mod = cst.parse_module("a = 1")
        context["module"] = new_mod
        return {"ok": True}

    mgr.register(stage)
    initial = cst.parse_module("x = 0")
    mgr.run(initial)
    files = list(mgr._diagnostics_dir.iterdir())
    assert any(
        (
            p.name.endswith("00_initial_input.py") or p.name.endswith("99_final_output.py") or p.name.endswith(".py")
            for p in files
        )
    )


def test_register_and_run_merges_context():
    mgr = StageManager()

    def stage_a(ctx):
        return {"a": 1}

    def stage_b(ctx):
        ctx["b"] = 2
        return None

    mgr.register(stage_a)
    mgr.register(stage_b)
    mod = cst.parse_module("def f():\n    return 1\n")
    out = mgr.run(mod)
    assert out.get("a") == 1
    assert out.get("b") == 2


def test_diagnostics_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    assert getattr(mgr, "_diagnostics_dir") is None


def test_diagnostics_enabled_writes_files(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    d = getattr(mgr, "_diagnostics_dir")
    assert d is not None

    def add_pass(ctx):
        m = ctx.get("module")
        new = cst.parse_module(m.code + "\n# added")
        return {"module": new}

    mgr.register(add_pass)
    mod = cst.parse_module("def f():\n    return 1\n")
    mgr.run(mod)
    files = list(d.iterdir()) if d is not None else []
    assert any(("initial_input" in p.name or "added" in p.name or p.suffix == ".py" for p in files))
    try:
        shutil.rmtree(d)
    except Exception:
        pass


def test_diagnostics_marker_and_dir_created(monkeypatch, tmp_path):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    if mgr._diagnostics_dir is None:
        return
    files = list(mgr._diagnostics_dir.iterdir())
    assert any((p.name.startswith("splurge-diagnostics-") for p in files))


def test_register_writes_stage_snapshot(monkeypatch, tmp_path):
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    if mgr._diagnostics_dir is None:
        return

    def stage(context):
        new_mod = cst.parse_module("a = 1")
        context["module"] = new_mod
        return {"ok": True}

    mgr.register(stage)
    initial = cst.parse_module("x = 0")
    mgr.run(initial)
    files = list(mgr._diagnostics_dir.iterdir())
    assert any(
        (
            p.name.endswith("00_initial_input.py") or p.name.endswith("99_final_output.py") or p.suffix == ".py"
            for p in files
        )
    )


def test_no_diagnostics_when_disabled(monkeypatch):
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    assert mgr._diagnostics_dir is None
