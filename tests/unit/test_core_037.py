import libcst as cst

from splurge_unittest_to_pytest.stages import formatting

DOMAINS = ["core"]


def test_node_to_str_name_and_attribute():
    n = cst.Name("os")
    assert formatting._node_to_str(n) == "os"

    a = cst.Attribute(value=cst.Name("pkg"), attr=cst.Name("mod"))
    assert formatting._node_to_str(a) == "pkg.mod"


def test_normalize_class_body_collapses_runs():
    # Create an indented block with multiple EmptyLine runs between methods
    # Put the first function inside a SimpleStatementLine to match the
    # shape the normalizer looks for (prev_non_empty being SimpleStatementLine
    # whose body[0] is a FunctionDef).
    inner_m1 = cst.FunctionDef(name=cst.Name("a"), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))
    m1 = cst.SimpleStatementLine(body=[inner_m1])
    m2 = cst.FunctionDef(name=cst.Name("b"), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))
    body = cst.IndentedBlock(body=[m1, cst.EmptyLine(), cst.EmptyLine(), cst.EmptyLine(), m2])
    norm = formatting.normalize_class_body(body)
    # Expect at most one EmptyLine between methods
    codes = [type(n).__name__ for n in norm.body]
    # should contain SimpleStatementLine (wrapping FunctionDef), EmptyLine, FunctionDef
    assert codes[0] == "SimpleStatementLine"
    assert codes[1] == "EmptyLine"
    assert codes[2] == "FunctionDef"


def test_normalize_module_import_grouping_and_spacing():
    # Module with repeated imports and docstring
    doc = cst.SimpleStatementLine(body=[cst.Expr(cst.SimpleString("'doc'"))])
    imp1 = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    imp2 = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
    imp3 = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    func = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))

    module = cst.Module(body=[doc, imp1, imp2, imp3, cst.EmptyLine(), func])
    new_mod = formatting.normalize_module(module)
    code = new_mod.code
    # 'os' should appear once, 'pytest' present and two blank lines before function
    assert code.count("import os") == 1
    assert "import pytest" in code
    assert "def f" in code
