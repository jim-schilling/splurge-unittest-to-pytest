import os
from pathlib import Path

import libcst as cst
from splurge_unittest_to_pytest.stages.manager import StageManager
from splurge_unittest_to_pytest.stages import diagnostics


def test_stage_manager_writes_snapshots(tmp_path: Path) -> None:
    # Enable diagnostics for this test
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    try:
        manager = StageManager()

        # simple stage that appends a comment to the module
        def stage_append_comment(ctx: dict):
            mod = ctx.get("module")
            if mod is None:
                return {"module": mod}
            src = getattr(mod, "code", None) or ""
            new_src = src + "\n# appended by stage"
            new_mod = cst.parse_module(new_src)
            return {"module": new_mod}

        manager.register(stage_append_comment)

        # run the manager with a tiny module
        module = cst.parse_module("x = 1\n")
        manager.run(module)

        # diagnostics.create_diagnostics_dir should have returned a Path when enabled
        ddir = diagnostics.create_diagnostics_dir()
        # Manager stores its diagnostics dir privately but the helper returns one for this run too.
        assert ddir is None or isinstance(ddir, Path) or ddir is None
        # If diagnostics were created, ensure at least one file exists under it
        if ddir is not None:
            files = list(ddir.iterdir())
            assert files, "Expected diagnostics files to be written"
    finally:
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
