import libcst as cst

from splurge_unittest_to_pytest.converter import helpers, imports, name_replacer, params


def test_replace_names_handles_cls_attribute_and_bare_name():
    src = "inst = cls.some_attr\nother = some_attr\n"
    module = cst.parse_module(src)
    stmts = list(module.body)
    replaced = name_replacer.replace_names_in_statements(stmts, "some_attr", "_val")
    code = cst.Module(body=replaced).code
    assert "_val" in code
    assert "cls.some_attr" not in code


def test_remove_unittest_import_removes_import_node():
    imp = cst.Import(names=[cst.ImportAlias(name=cst.Name("unittest"))])
    out = imports.remove_unittest_import(imp)
    assert out is cst.RemovalSentinel.REMOVE


def test_has_pytest_import_detects_from_import():
    module = cst.parse_module("from pytest import mark\n")
    assert imports.has_pytest_import(module)


def test_append_fixture_params_preserves_existing():
    existing = cst.Parameters(params=[cst.Param(name=cst.Name("req"))])
    combined = params.append_fixture_params(existing, ["extra"])
    names = [p.name.value for p in combined.params]
    assert "req" in names and "extra" in names


def test_parse_method_patterns_dedupes_and_splits():
    res = helpers.parse_method_patterns(("a,b", "a", "  "))
    assert res == ["a", "b"]
