import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_inserts_import_after_docstring():
    src = textwrap.dedent('''
    """Module docstring."""

    # some top comment

    def foo():
        pass
    ''')

    mod = cst.parse_module(src)
    ctx = {"module": mod, "needs_pytest_import": True}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # pytest import should be after docstring (i.e., not before the triple-quoted string)
    assert code.index('"""Module docstring."""') < code.index("import pytest")
