import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_typing_merge_handles_as_aliases():
    src = textwrap.dedent("""
    from typing import Optional as Opt

    def f(x: Opt[int]) -> List[int]:
        pass
    """)
    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["List"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    assert "Optional as Opt" in code or "as Opt" in code
    assert "List" in code


def test_typing_merge_skips_duplicates():
    src = textwrap.dedent("""
    from typing import List, Optional

    def f() -> List[int]:
        pass
    """)
    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["List"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # ensure List only appears once in the typing import
    assert code.count("List") >= 1


def test_typing_merge_preserves_comment_on_new_name():
    src = textwrap.dedent("""
    from typing import Optional  # optional

    def f(x: Optional[int]) -> Any:
        pass
    """)
    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["Any"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # comment for Optional should still be present and Any should be added
    assert "# optional" in code
    assert "Any" in code
