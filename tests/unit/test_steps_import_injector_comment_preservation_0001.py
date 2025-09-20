import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_merging_multiple_typing_blocks_preserves_comments_and_parentheses():
    src = textwrap.dedent("""
    # header
    from typing import Optional  # top-comment
    from typing import (
        List,  # list-comment
    )  # end-parens

    def f(x: Optional[int]) -> List[int]:
        pass
    """)

    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["Any"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code

    # There should be exactly one consolidated typing import
    assert code.count("from typing import") == 1

    # All original comments should be preserved somewhere in the output
    assert "# top-comment" in code
    assert "# list-comment" in code
    assert "# end-parens" in code

    # Parentheses should be preserved (we expect parenthesized import)
    assert "(" in code and ")" in code
