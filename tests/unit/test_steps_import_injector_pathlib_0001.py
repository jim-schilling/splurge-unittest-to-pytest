import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_inserts_pathlib_for_path_usage():
    src = textwrap.dedent("""
    def f():
        p = Path("/tmp")
        return p
    """)

    mod = cst.parse_module(src)
    ctx = {"module": mod}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    assert "from pathlib import Path" in code or "import pathlib" in code
