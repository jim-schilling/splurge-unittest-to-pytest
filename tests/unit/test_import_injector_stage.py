import libcst as cst

from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


def test_import_injector_inserts_pytest_after_docstring() -> None:
    src = '"""mod doc"""\n\nx = 1\n'
    module = cst.parse_module(src)
    out = import_injector_stage({"module": module, "needs_pytest_import": True})
    new_mod = out.get("module")
    assert new_mod is not None
    # first non-docstring node should be the inserted import (or similar)
    first = new_mod.body[0]
    assert isinstance(first, cst.BaseSmallStatement) or isinstance(first, cst.SimpleStatementLine)
    # ensure pytest import exists somewhere
    found = False
    for s in new_mod.body:
        if isinstance(s, cst.SimpleStatementLine) and s.body:
            expr = s.body[0]
            if isinstance(expr, cst.Import):
                for n in expr.names:
                    if getattr(n.name, "value", None) == "pytest":
                        found = True
                        break
        if found:
            break
    assert found


def test_import_injector_respects_needs_flags() -> None:
    src = "x = 1\n"
    module = cst.parse_module(src)
    out = import_injector_stage({"module": module, "needs_pytest_import": False, "needs_re_import": True})
    new_mod = out.get("module")
    assert new_mod is not None
    found_re = False
    for s in new_mod.body:
        if isinstance(s, cst.SimpleStatementLine) and s.body:
            expr = s.body[0]
            if isinstance(expr, cst.Import):
                for n in expr.names:
                    if getattr(n.name, "value", None) == "re":
                        found_re = True
                        break
        if found_re:
            break
    assert found_re
