import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_multiple_typing_blocks_merge_correctly():
    src = textwrap.dedent("""
    from typing import Optional  # top
    from typing import (
        List,  # list comment
    )

    def f(x: Optional[int]) -> List[int]:
        pass
    """)
    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["Any"]}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # comments from both blocks should still be present
    assert "# top" in code
    assert "# list comment" in code
    assert "Any" in code


def test_parenthesized_as_aliases_preserved():
    src = textwrap.dedent("""
    from typing import (
        Optional as Opt,  # opt
    )

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
    assert "# opt" in code


def test_insert_imports_idempotent():
    src = textwrap.dedent("""
    from typing import Optional

    def f(x: Optional[int]) -> List[int]:
        pass
    """)
    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_typing_names": ["List"]}
    res1 = InsertImportsStep().execute(ctx, {})
    mod1 = res1.delta.values.get("module")
    res2 = InsertImportsStep().execute({"module": mod1, "needs_typing_names": ["List"]}, {})
    mod2 = res2.delta.values.get("module")
    assert mod1.code == mod2.code
