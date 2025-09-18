from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


def _module_from_code(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_import_injector_respects_alias_imports() -> None:
    src = """
import pytest as pt

def test_one():
    pt.raises(Exception)
"""
    mod = _module_from_code(src)
    res = import_injector_stage({"module": mod})
    out = res.get("module")
    assert isinstance(out, cst.Module)
    # There should be no duplicate import of pytest (alias present)
    # Inspect module imports: ensure only the aliased import exists
    imports = [s for s in out.body if isinstance(s, cst.SimpleStatementLine) and s.body]
    pytest_imports = 0
    for stmt in imports:
        first = stmt.body[0]
        if isinstance(first, cst.Import):
            for name in first.names:
                if getattr(name.name, "value", None) == "pytest":
                    pytest_imports += 1
        if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "pytest":
            pytest_imports += 1
    # Should be exactly one pytest import (the aliased one)
    assert pytest_imports == 1


def test_import_injector_inserts_pathlib_when_needed() -> None:
    src = """
from typing import Any

def foo():
    p: Path
"""
    mod = _module_from_code(src)
    res = import_injector_stage({"module": mod, "needs_typing_names": ["Any", "Path"]})
    out = res.get("module")
    assert isinstance(out, cst.Module)
    text = out.code if hasattr(out, "code") else ""
    # ensure pathlib import was added (from pathlib import Path)
    assert "from pathlib import Path" in text
