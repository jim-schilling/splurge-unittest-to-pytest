import shutil
import libcst as cst

from splurge_unittest_to_pytest.stages.manager import StageManager


def test_register_and_run_merges_context():
    mgr = StageManager()

    def stage_a(ctx):
        return {"a": 1}

    def stage_b(ctx):
        # mutate context in-place
        ctx["b"] = 2
        return None

    mgr.register(stage_a)
    mgr.register(stage_b)

    mod = cst.parse_module("def f():\n    return 1\n")
    out = mgr.run(mod)
    assert out.get("a") == 1
    assert out.get("b") == 2


def test_diagnostics_disabled_by_default(tmp_path, monkeypatch):
    # ensure env var not set
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    # diagnostics dir should be None
    assert getattr(mgr, "_diagnostics_dir") is None


def test_diagnostics_enabled_writes_files(tmp_path, monkeypatch):
    # enable diagnostics
    monkeypatch.setenv("SPLURGE_ENABLE_DIAGNOSTICS", "1")
    mgr = StageManager()
    d = getattr(mgr, "_diagnostics_dir")
    assert d is not None

    # run a stage that mutates module
    def add_pass(ctx):
        m = ctx.get("module")
        # append a new simple function via code replace
        new = cst.parse_module(m.code + "\n# added")
        return {"module": new}

    mgr.register(add_pass)
    mod = cst.parse_module("def f():\n    return 1\n")
    mgr.run(mod)
    # diagnostics dir should contain files
    files = list(d.iterdir()) if d is not None else []
    assert any("initial_input" in p.name or "added" in p.name or p.suffix == ".py" for p in files)
    # cleanup
    try:
        shutil.rmtree(d)
    except Exception:
        pass
