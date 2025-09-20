import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import DetectNeedsStep, InsertImportsStep


def test_does_not_insert_duplicate_pytest_when_present_or_aliased():
    src = textwrap.dedent("""
    import pytest as _pytest

    def test_x():
        _pytest.mark.something
    """)

    mod = cst.parse_module(src)
    ctx = {"module": mod}
    det = DetectNeedsStep().execute(ctx, {})
    res = InsertImportsStep().execute({"module": mod, **det.delta.values}, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # should only have the existing alias import, not a new `import pytest`
    assert code.count("import pytest") <= 1
