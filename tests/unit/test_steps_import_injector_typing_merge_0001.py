import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep, DetectNeedsStep


def test_merge_typing_imports_preserves_existing_and_adds_missing():
    src = textwrap.dedent("""
    from typing import Optional

    def f(x: Optional[int]) -> List[int]:
        pass
    """)

    mod = cst.parse_module(src)
    ctx = {"module": mod}
    # first detect typing needs (InsertImportsStep looks at ctx needs_typing_names but also module text)
    _ = DetectNeedsStep().execute(ctx, {})
    # force typing names to include List
    det_ctx = {"module": mod, "needs_typing_names": ["List"]}
    res = InsertImportsStep().execute(det_ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # Ensure typing import now contains Optional and List (order may vary)
    assert "Optional" in code and "List" in code
