import textwrap
import libcst as cst
from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def _module_from_code(code: str) -> cst.Module:
    return cst.parse_module(textwrap.dedent(code))


def test_insert_pytest_when_needed_and_missing():
    code = """
    def test_something():
        assert True
    """
    mod = _module_from_code(code)
    step = InsertImportsStep()
    result = step.execute({"module": mod, "needs_pytest_import": True}, None)
    new_mod = result.delta.values.get("module")
    assert new_mod is not None
    text = new_mod.code
    assert "import pytest" in text


def test_preserve_existing_imports_and_add_missing():
    code = "import os\n\ndef foo():\n    pass\n"
    mod = _module_from_code(code)
    step = InsertImportsStep()
    result = step.execute({"module": mod, "needs_re_import": True, "needs_os_import": True}, None)
    new_mod = result.delta.values.get("module")
    assert new_mod is not None
    text = new_mod.code
    # os already present, re should be added
    assert "import re" in text
    assert text.count("import os") == 1


def test_typing_cleanup_and_path_insertion():
    code = "from typing import Any\n\nX: Any\n"
    mod = _module_from_code(code)
    step = InsertImportsStep()
    # request Path as needed
    result = step.execute({"module": mod, "needs_typing_names": ["Path"]}, None)
    new_mod = result.delta.values.get("module")
    assert new_mod is not None
    text = new_mod.code
    # Path should cause pathlib.Path import
    assert "from pathlib import Path" in text or "import pathlib" in text
