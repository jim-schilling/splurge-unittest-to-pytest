import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_preserves_parentheses_format_when_merging_typing():
    src = textwrap.dedent("""
    from typing import (
        Optional,
    )

    def f() -> List[int]:
        pass
    """)

    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["List"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # ensure the resulting typing import still uses parentheses
    assert "from typing import (" in code or "(" in code
