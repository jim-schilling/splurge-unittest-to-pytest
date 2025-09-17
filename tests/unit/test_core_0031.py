import libcst as cst
from splurge_unittest_to_pytest.converter import imports

DOMAINS = ["core"]


def test_has_and_add_pytest_import_when_missing():
    src = """\n# module with no pytest import\nimport os\n\n"""
    module = cst.parse_module(src)
    assert not imports.has_pytest_import(module)
    new_mod = imports.add_pytest_import(module)
    assert imports.has_pytest_import(new_mod)
    # adding again returns the same structure (idempotent)
    new_mod2 = imports.add_pytest_import(new_mod)
    assert imports.has_pytest_import(new_mod2)


def test_remove_unittest_importfrom_and_import():
    # test ImportFrom removal
    src = "from unittest import TestCase, mock\nimport unittest\nimport something_else\n"
    module = cst.parse_module(src)
    # Walk module body and apply helpers to ImportFrom and Import nodes
    new_body = []
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom):
                res = imports.remove_unittest_importfrom(first)
                if res is cst.RemovalSentinel.REMOVE:
                    continue
                new_body.append(stmt)
            elif isinstance(first, cst.Import):
                res = imports.remove_unittest_import(first)
                if res is cst.RemovalSentinel.REMOVE:
                    continue
                new_body.append(stmt)
            else:
                new_body.append(stmt)
    # ensure that unittest imports got removed
    new_module = cst.Module(body=new_body)
    text = new_module.code
    assert "unittest" not in text
