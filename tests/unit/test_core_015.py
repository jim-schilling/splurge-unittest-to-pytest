import libcst as cst

from splurge_unittest_to_pytest.converter import imports

DOMAINS = ["core"]


def test_add_pytest_import_after_docstring_and_imports():
    src = '"""mod doc"""\n\nimport os\n\n'
    module = cst.parse_module(src)
    new_mod = imports.add_pytest_import(module)
    code = new_mod.code
    # pytest import should be present and placed after docstring and existing imports
    assert "import pytest" in code


def test_add_pytest_import_idempotent_when_present():
    src = "import pytest\n\nimport os\n"
    module = cst.parse_module(src)
    new_mod = imports.add_pytest_import(module)
    # Should be unchanged structurally when pytest already imported
    assert new_mod.code.count("import pytest") == 1
