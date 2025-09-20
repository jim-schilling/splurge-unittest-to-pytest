import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import (
    _find_typing_indices,
    _merge_typing_into_existing,
)


def test_preserved_comments_not_duplicated_when_merging():
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

    # find indices and perform merge using the helper (pick first typing idx)
    typing_idxs = _find_typing_indices(mod)
    assert typing_idxs, "expected typing import indices"

    merged = _merge_typing_into_existing(mod, typing_idxs[0], set())
    code = merged.code

    # Ensure each preserved comment appears exactly once in the output
    assert code.count("# keep-optional") == 1
    assert code.count("# comment-on-list") == 1
    assert code.count("# end-parens") == 1
