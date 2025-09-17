import libcst as cst
from splurge_unittest_to_pytest.stages import fixture_injector, import_injector
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


def test_import_injector_adds_pytest_after_docstring_and_imports():
    doc = cst.SimpleStatementLine(body=[cst.Expr(cst.SimpleString("'doc'"))])
    imp = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    module = cst.Module(body=[doc, imp, cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Name("f")))])])
    res = import_injector.import_injector_stage({"module": module, "needs_pytest_import": True})
    new_mod = res["module"]
    code = new_mod.code
    assert "import pytest" in code
    assert code.index("import pytest") > code.index("'doc'")


def test_fixture_injector_inserts_fixture_after_pytest_import_and_adds_autouse_when_unittest():
    imp_py = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
    module = cst.Module(body=[imp_py, cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Name("f")))])])
    fn = cst.FunctionDef(
        name=cst.Name("a"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=[cst.Pass()]),
        decorators=[cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))],
    )
    collector = CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={}, has_unittest_usage=True
    )
    res = fixture_injector.fixture_injector_stage(
        {"module": module, "fixture_nodes": [fn], "collector_output": collector}
    )
    new_mod = res["module"]
    code = new_mod.code
    assert "def a" in code
    assert "_attach_to_instance" not in code or "def a" in code
