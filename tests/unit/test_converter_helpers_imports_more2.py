import libcst as cst

from splurge_unittest_to_pytest.converter import helpers, imports


def test_has_meaningful_changes_with_normalizer_exception(monkeypatch):
    # Force formatting.normalize_module to raise so we exercise AST comparison
    import splurge_unittest_to_pytest.stages.formatting as formatting

    monkeypatch.setattr(formatting, "normalize_module", lambda m: (_ for _ in ()).throw(Exception("boom")))

    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 1\n"
    assert helpers.has_meaningful_changes(orig, conv) is False


def test_has_meaningful_changes_ast_detects_change(monkeypatch):
    import splurge_unittest_to_pytest.stages.formatting as formatting

    monkeypatch.setattr(formatting, "normalize_module", lambda m: (_ for _ in ()).throw(Exception("boom")))

    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv) is True


def test_remove_unittest_import_with_alias():
    imp = cst.Import(names=[cst.ImportAlias(name=cst.Name("unittest"), asname=cst.AsName(name=cst.Name("u")))])
    out = imports.remove_unittest_import(imp)
    assert out is cst.RemovalSentinel.REMOVE


def test_has_pytest_import_with_alias_import():
    module = cst.parse_module("import pytest as p\n")
    assert imports.has_pytest_import(module)
