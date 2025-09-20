import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def _run_insert(src: str, ctx_overrides: dict | None = None) -> str:
    mod = cst.parse_module(textwrap.dedent(src))
    ctx = {"module": mod}
    if ctx_overrides:
        ctx.update(ctx_overrides)
    step = InsertImportsStep()
    res = step.execute(ctx, resources=None)
    # Extract the module from the returned context delta
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    return new_mod.code


def test_insert_imports_idempotent():
    src = """
# file header
from typing import Optional  # marker

def f(x: Optional[int]):
    pass
"""
    first = _run_insert(src)
    second = _run_insert(first)
    assert first == second
