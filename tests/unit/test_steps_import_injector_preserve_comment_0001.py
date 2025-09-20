import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_preserves_inline_comment_on_typing_import_merge():
    src = textwrap.dedent("""
    from typing import Optional  # keep-me

    def f(x: Optional[int]) -> List[int]:
        pass
    """)

    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["List"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # ensure comment survived the merge on the typing import line
    assert "# keep-me" in code
