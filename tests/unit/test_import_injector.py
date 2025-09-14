from __future__ import annotations

import libcst as cst
from typing import cast

from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


def _find_import_from(module: cst.Module, module_name: str) -> cst.ImportFrom | None:
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == module_name:
                return first
    return None


def test_import_injector_inserts_pathlib_and_typing() -> None:
    # start with an empty module
    module = cst.parse_module("")
    context = {
        "module": module,
        # Request typing names including Path which should be special-cased
        "needs_typing_names": ["Generator", "Dict", "Path"],
    }

    out = import_injector_stage(context)
    assert isinstance(out, dict)
    new_module = out.get("module")
    assert isinstance(new_module, cst.Module)

    # Check pathlib import for Path
    pathlib_import = _find_import_from(new_module, "pathlib")
    assert pathlib_import is not None, "expected 'from pathlib import Path' to be inserted"
    assert any(getattr(alias.name, "value", None) == "Path" for alias in getattr(pathlib_import, "names", []))

    # Check typing import for Generator and Dict
    typing_import = _find_import_from(new_module, "typing")
    assert typing_import is not None, "expected 'from typing import ...' to be inserted"
    typing_names = {getattr(alias.name, "value", None) for alias in getattr(typing_import, "names", [])}
    assert "Generator" in typing_names and "Dict" in typing_names


def test_import_injector_inserts_after_docstring() -> None:
    src = '"""module doc"""\n\nclass A:\n    pass\n'
    module = cst.parse_module(src)
    ctx: dict[str, object] = {"module": module}
    res = import_injector_stage(ctx)
    new_module = cast(cst.Module, res.get("module"))
    # first stmt should remain docstring, second should be import
    assert isinstance(new_module.body[0], cst.SimpleStatementLine)
    assert isinstance(new_module.body[1], cst.SimpleStatementLine)
    # the import should contain pytest
    import_stmt = new_module.body[1].body[0]
    assert isinstance(import_stmt, cst.Import)
    assert import_stmt.names[0].name.value == "pytest"


def test_import_injector_no_duplicate() -> None:
    src = "import pytest\n\nclass A:\n    pass\n"
    module = cst.parse_module(src)
    ctx: dict[str, object] = {"module": module}
    res = import_injector_stage(ctx)
    new_module = cast(cst.Module, res.get("module"))
    # ensure still only one import pytest (first stmt)
    imports = [s.body[0] for s in new_module.body if isinstance(s, cst.SimpleStatementLine) and s.body]
    pytest_imports = [i for i in imports if isinstance(i, cst.Import) and i.names[0].name.value == "pytest"]
    assert len(pytest_imports) == 1


def test_preserve_existing_typing_imports_and_add_missing() -> None:
    # module already imports Generator from typing; request Generator and Dict
    src = "from typing import Generator\n\nclass A:\n    pass\n"
    module = cst.parse_module(src)
    ctx = {"module": module, "needs_typing_names": ["Generator", "Dict"]}
    res = import_injector_stage(ctx)
    new_module = res.get("module")
    # Ensure typing import exists and contains both names (Generator already present, Dict added)
    typing_import = _find_import_from(new_module, "typing")
    assert typing_import is not None
    names = {getattr(alias.name, "value", None) for alias in getattr(typing_import, "names", [])}
    assert "Generator" in names and "Dict" in names


def test_insertion_order_with_existing_imports() -> None:
    # If module already has some imports, new imports should be placed after the last import
    src = "import os\nimport sys\n\n# code\n"
    module = cst.parse_module(src)
    ctx = {"module": module, "needs_typing_names": ["Path"]}
    res = import_injector_stage(ctx)
    new_module = res.get("module")
    # find index of last original import (should be 1) and index of inserted pathlib import (should be 2)
    # We look for the first ImportFrom whose module is pathlib
    idx_pathlib = None
    for i, stmt in enumerate(new_module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "pathlib":
                idx_pathlib = i
                break
    assert idx_pathlib is not None
    # expect it to come after existing imports (which were at 0 and 1)
    assert idx_pathlib > 1


def test_no_duplicate_pathlib_import_when_present() -> None:
    # If module already has `from pathlib import Path`, don't insert another
    src = "from pathlib import Path\n\nclass A:\n    pass\n"
    module = cst.parse_module(src)
    ctx = {"module": module, "needs_typing_names": ["Path"]}
    res = import_injector_stage(ctx)
    new_module = res.get("module")
    # count pathlib imports
    pathlib_imports = [
        s
        for s in new_module.body
        if isinstance(s, cst.SimpleStatementLine)
        and s.body
        and isinstance(s.body[0], cst.ImportFrom)
        and getattr(s.body[0].module, "value", None) == "pathlib"
    ]
    assert len(pathlib_imports) == 1


def test_typing_import_names_are_sorted_deterministically() -> None:
    # request names in a non-sorted order and ensure the inserted import is sorted
    module = cst.parse_module("")
    ctx = {"module": module, "needs_typing_names": ["Dict", "Generator", "Any"]}
    res = import_injector_stage(ctx)
    new_module = res.get("module")
    typing_import = _find_import_from(new_module, "typing")
    assert typing_import is not None
    names = [getattr(alias.name, "value", None) for alias in getattr(typing_import, "names", [])]
    assert names == sorted(names), "typing import names should be sorted deterministically"


def test_tidy_stage_preserves_and_dedupes_imports() -> None:
    # create a module that will receive duplicate imports and then run tidy_stage
    src = "import os\nfrom pathlib import Path\n\n# code\n"
    module = cst.parse_module(src)
    # simulate needing Path insertion (should not duplicate)
    ctx = {"module": module, "needs_typing_names": ["Path"]}
    res = import_injector_stage(ctx)
    from splurge_unittest_to_pytest.stages.tidy import tidy_stage

    new_module = res.get("module")
    tidy_out = tidy_stage({"module": new_module})
    final_module = tidy_out.get("module")
    # ensure only one pathlib import remains
    pathlib_imports = [
        s
        for s in final_module.body
        if isinstance(s, cst.SimpleStatementLine)
        and s.body
        and isinstance(s.body[0], cst.ImportFrom)
        and getattr(s.body[0].module, "value", None) == "pathlib"
    ]
    assert len(pathlib_imports) == 1
