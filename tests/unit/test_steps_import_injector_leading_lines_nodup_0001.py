import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import (
    _find_typing_indices,
    _merge_typing_into_existing,
    _render_stmt_comments,
)


def test_no_duplicate_leading_lines_after_merge():
    src = textwrap.dedent("""
    # module header
    from typing import Optional  # keep-optional
    from typing import (
        List,  # comment-on-list
    )  # end-parens

    def f(x: Optional[int]) -> List[int]:
        pass
    """)

    mod = cst.parse_module(src)
    typing_idxs = _find_typing_indices(mod)
    assert typing_idxs, "expected typing import indices"

    merged = _merge_typing_into_existing(mod, typing_idxs[0], set())

    # Find the first SimpleStatementLine that is the typing import
    for stmt in merged.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "typing":
                # leading_lines should be a sequence of EmptyLine; collect their comments
                leading = getattr(stmt, "leading_lines", []) or []
                comments = [
                    getattr(ll.comment, "value", None) for ll in leading if getattr(ll, "comment", None) is not None
                ]
                # comments should be unique
                assert len(comments) == len(set(comments))
                # the rendered inline/trailing comments should also include these preserved comments
                rendered = _render_stmt_comments(stmt)
                for c in comments:
                    # comment value includes the '#', so ensure it's present in rendered output
                    assert c in rendered or c in stmt.code
                break
    else:
        assert False, "no typing import found in merged module"
