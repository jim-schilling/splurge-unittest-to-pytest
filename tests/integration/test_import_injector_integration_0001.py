import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.import_injector_tasks import (
    DetectNeedsCstTask,
    InsertImportsCstTask,
)


def _module(code: str) -> cst.Module:
    return cst.parse_module(textwrap.dedent(code))


def run_import_injector_pipeline(module: cst.Module, extra_ctx: dict | None = None) -> cst.Module:
    """Run the two import-injector tasks sequentially and return the final module.

    This mirrors the stage pipeline: detect needs -> insert imports.
    """
    ctx: dict = {"module": module}
    if extra_ctx:
        ctx.update(extra_ctx)

    detect_task = DetectNeedsCstTask()
    res1 = detect_task.execute(ctx, None)
    # merge returned values into context
    values1 = getattr(res1, "delta").values or {}
    ctx.update(values1)

    insert_task = InsertImportsCstTask()
    res2 = insert_task.execute(ctx, None)
    values2 = getattr(res2, "delta").values or {}
    final_mod = values2.get("module")
    return final_mod


def test_import_injector_end_to_end():
    code = '''
    """My module doc"""

    import os
    import re
    import pytest

    @pytest.mark.slow
    def test_it():
        p: "Path"
        assert os.path

    def uses_re():
        return re.match("a", "a")
    '''

    mod = _module(code)
    # Request Path typing name explicitly
    final = run_import_injector_pipeline(mod, extra_ctx={"needs_typing_names": ["Path"]})
    assert final is not None
    text = final.code

    # imports should include pytest, re and a pathlib import
    assert text.count("import pytest") == 1
    assert "import re" in text
    assert ("from pathlib import Path" in text) or ("import pathlib" in text)

    # first import should appear after the module docstring
    # find docstring node then ensure next nodes include imports
    body = final.body
    assert len(body) >= 2
    # the second and third nodes should include at least one import
    assert any(isinstance(n.body[0], (cst.Import, cst.ImportFrom)) for n in body[1:4])
