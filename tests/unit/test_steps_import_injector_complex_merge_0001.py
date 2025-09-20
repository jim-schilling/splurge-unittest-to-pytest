import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep, _merge_typing_into_existing


def test_complex_typing_import_merge_preserves_comments_and_whitespace():
    src = textwrap.dedent("""
    # module header
    from typing import Optional  # keep-optional
    from typing import (
        List,  # comment-on-list
        Tuple  # trailing-tuple
    )  # end-parens-comment

    def f(x: Optional[int]) -> List[int]:
        pass
    """)

    mod = cst.parse_module(src)
    # run detect/insert behavior via InsertImportsStep path
    ctx = {"module": mod, "needs_typing_names": ["Any"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # comments should survive
    assert "# keep-optional" in code
    assert "# comment-on-list" in code
    assert "# trailing-tuple" in code
    assert "# end-parens-comment" in code

    # Also validate the helper directly: merge 'Any' into the first typing import
    mod2 = cst.parse_module(src)
    # find existing typing import index
    idx = None
    for i, stmt in enumerate(mod2.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], cst.ImportFrom):
            if getattr(stmt.body[0].module, "value", None) == "typing":
                idx = i
                break
    assert idx is not None
    merged = _merge_typing_into_existing(mod2, idx, {"Any"})
    assert "Any" in merged.code
    assert "# comment-on-list" in merged.code
