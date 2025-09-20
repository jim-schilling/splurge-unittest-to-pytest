import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import DetectNeedsStep, InsertImportsStep


def test_detects_pathlib_alias_and_does_not_duplicate():
    src = textwrap.dedent("""
    import pathlib as pl

    def f():
        p = pl.Path('/tmp')
        return p
    """)

    mod = cst.parse_module(src)
    det = DetectNeedsStep().execute({"module": mod}, {})
    res = InsertImportsStep().execute({"module": mod, **det.delta.values}, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # Ensure we didn't add a redundant `from pathlib import Path`
    assert code.count("pathlib") >= 1
    assert "from pathlib import Path" not in code
