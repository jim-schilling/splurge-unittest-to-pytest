import libcst as cst

from splurge_unittest_to_pytest.converter.imports import add_pytest_import, has_pytest_import


def test_add_pytest_import_inserts_after_docstring():
    src = '"""module doc"""\n\n'
    module = cst.parse_module(src)
    new_module = add_pytest_import(module)
    assert has_pytest_import(new_module)


def test_add_pytest_import_after_existing_imports():
    src = "import os\nimport sys\n"
    module = cst.parse_module(src)
    new_module = add_pytest_import(module)
    assert has_pytest_import(new_module)
