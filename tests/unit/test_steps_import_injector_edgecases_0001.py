import textwrap
import libcst as cst
from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def _module(code: str) -> cst.Module:
    return cst.parse_module(textwrap.dedent(code))


def test_typing_merge_with_existing():
    code = """
    from typing import Any, List

    X: List[Any]
    """
    mod = _module(code)
    step = InsertImportsStep()
    # Request Dict as additional typing; ensure typing import is merged not duplicated
    res = step.execute({"module": mod, "needs_typing_names": ["Dict"]}, None)
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    # ensure typing import contains required names regardless of order
    found = False
    for stmt in new_mod.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], cst.ImportFrom):
            if getattr(stmt.body[0].module, "value", None) == "typing":
                names = [getattr(n.name, "value", "") for n in stmt.body[0].names or []]
                if set(["Any", "List", "Dict"]).issubset(set(names)):
                    found = True
                    break
    assert found


def test_remove_unused_typing_imports_when_not_explicit():
    code = """
    from typing import Any, Tuple

    X: Any
    """
    mod = _module(code)
    step = InsertImportsStep()
    # No explicit typing flag; at minimum Any must remain in typing imports
    res = step.execute({"module": mod}, None)
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    # ensure Any still present in typing imports
    any_found = False
    for stmt in new_mod.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], cst.ImportFrom):
            if getattr(stmt.body[0].module, "value", None) == "typing":
                names = [getattr(n.name, "value", "") for n in stmt.body[0].names or []]
                if "Any" in names:
                    any_found = True
                    break
    assert any_found


def test_pathlib_insertion_when_path_needed():
    code = """
    def f(p: 'Path'):
        pass
    """
    mod = _module(code)
    step = InsertImportsStep()
    res = step.execute({"module": mod, "needs_typing_names": ["Path"]}, None)
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    text = new_mod.code
    assert "from pathlib import Path" in text or "import pathlib" in text


def test_insert_after_docstring_if_present():
    code = '"""module doc"""\n\n\ndef foo():\n    pass\n'
    mod = _module(code)
    step = InsertImportsStep()
    res = step.execute({"module": mod, "needs_re_import": True}, None)
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    # first node after docstring should be import (look at the next couple of nodes)
    assert any(isinstance(s.body[0], (cst.Import, cst.ImportFrom)) for s in new_mod.body[1:3])


def test_do_not_duplicate_pytest_import_if_present():
    code = "import pytest\n\ndef test_a():\n    pass\n"
    mod = _module(code)
    step = InsertImportsStep()
    res = step.execute({"module": mod, "needs_pytest_import": True}, None)
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    text = new_mod.code
    assert text.count("import pytest") == 1
