import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import import_injector


def make_module(src: str) -> cst.Module:
    return cst.parse_module(textwrap.dedent(src))


def test_no_module_returns_empty():
    assert import_injector.import_injector_stage({}) == {}


def test_default_inserts_pytest_when_no_flags():
    m = make_module("# no imports\n\ndef f():\n    pass\n")
    out = import_injector.import_injector_stage({"module": m})
    assert "module" in out
    new_mod = out["module"]
    first = new_mod.body[0]
    assert isinstance(first, cst.SimpleStatementLine)
    assert isinstance(first.body[0], cst.Import)
    assert first.body[0].names[0].name.value == "pytest"


def test_inserts_after_docstring():
    src = '"""docstring"""\n\nimport os\n\nx = 1\n'
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_pytest_import": True})
    new_mod = out["module"]
    inserts = [s for s in new_mod.body if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Import)]
    names = [st.body[0].names[0].name.value for st in inserts]
    assert "os" in names
    assert "pytest" in names


def test_does_not_duplicate_existing_imports():
    src = "import pytest\n\nx=1\n"
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_pytest_import": True})
    new_mod = out["module"]
    pytest_imports = [
        s
        for s in new_mod.body
        if isinstance(s, cst.SimpleStatementLine)
        and isinstance(s.body[0], cst.Import)
        and (s.body[0].names[0].name.value == "pytest")
    ]
    assert len(pytest_imports) == 1


def test_typing_and_pathlib_insertion_and_merge():
    src = "x=1\n"
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_typing_names": ["Any", "Path"]})
    new_mod = out["module"]
    found_pathlib = any(
        (
            isinstance(s.body[0], cst.ImportFrom) and getattr(s.body[0].module, "value", None) == "pathlib"
            for s in new_mod.body
            if isinstance(s, cst.SimpleStatementLine)
        )
    )
    assert found_pathlib
    typing_stmt = None
    for s in new_mod.body:
        if (
            isinstance(s, cst.SimpleStatementLine)
            and isinstance(s.body[0], cst.ImportFrom)
            and (getattr(s.body[0].module, "value", None) == "typing")
        ):
            typing_stmt = s
            break
    assert typing_stmt is not None
    imported = {alias.name.value for alias in typing_stmt.body[0].names}
    assert "Any" in imported


def test_merge_into_existing_typing_import():
    src = "from typing import List\n\nx=1\n"
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_typing_names": ["Any", "List"]})
    new_mod = out["module"]
    typing_stmt = None
    for s in new_mod.body:
        if (
            isinstance(s, cst.SimpleStatementLine)
            and isinstance(s.body[0], cst.ImportFrom)
            and (getattr(s.body[0].module, "value", None) == "typing")
        ):
            typing_stmt = s
            break
    assert typing_stmt is not None
    imported = {alias.name.value for alias in typing_stmt.body[0].names}
    assert "Any" in imported and "List" in imported


def test_detects_pytest_usage_in_module_text():
    src = "def test():\n    pytest.raises(ValueError)\n"
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_pytest_import": False})
    new_mod = out["module"]
    assert any(
        (
            isinstance(s.body[0], cst.Import) and s.body[0].names[0].name.value == "pytest"
            for s in new_mod.body
            if isinstance(s, cst.SimpleStatementLine)
        )
    )
