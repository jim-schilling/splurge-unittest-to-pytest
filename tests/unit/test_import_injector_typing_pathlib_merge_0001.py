from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


def _find_import_from(module: cst.Module, module_name: str) -> cst.ImportFrom | None:
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == module_name:
                return first
    return None


def test_typing_and_pathlib_merge_with_existing_typing() -> None:
    """Ensure that when `typing` already imports some names and pathlib is needed,
    the injector merges new typing names into the existing `from typing import ...`
    and inserts `from pathlib import Path` only once.
    """
    src = "from typing import Any\n\nclass A:\n    pass\n"
    module = cst.parse_module(src)
    ctx = {"module": module, "needs_typing_names": ["Any", "Path", "Dict"], "needs_pathlib": True}

    res = import_injector_stage(ctx)
    assert isinstance(res, dict)
    new_module = res.get("module")
    assert isinstance(new_module, cst.Module)

    typing_import = _find_import_from(new_module, "typing")
    assert typing_import is not None, "expected 'from typing import ...' to be present"
    names = {getattr(alias.name, "value", None) for alias in getattr(typing_import, "names", [])}
    # Should contain original Any plus added Dict (Path is provided by pathlib import)
    assert "Any" in names and "Dict" in names

    pathlib_import = _find_import_from(new_module, "pathlib")
    assert pathlib_import is not None, "expected 'from pathlib import Path' to be inserted"
    pathlib_names = {getattr(alias.name, "value", None) for alias in getattr(pathlib_import, "names", [])}
    assert "Path" in pathlib_names

    # No duplicate pathlib imports
    pathlib_imports = [
        s
        for s in new_module.body
        if isinstance(s, cst.SimpleStatementLine)
        and s.body
        and isinstance(s.body[0], cst.ImportFrom)
        and (getattr(s.body[0].module, "value", None) == "pathlib")
    ]
    assert len(pathlib_imports) == 1
