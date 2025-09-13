import libcst as cst

from splurge_unittest_to_pytest.stages import fixture_injector, import_injector
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


def test_import_injector_adds_pytest_after_docstring_and_imports():
    # module with docstring and one import
    doc = cst.SimpleStatementLine(body=[cst.Expr(cst.SimpleString("'doc'"))])
    imp = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    module = cst.Module(body=[doc, imp, cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Name("f")))])])
    res = import_injector.import_injector_stage({"module": module, "needs_pytest_import": True})
    new_mod = res["module"]
    code = new_mod.code
    # pytest import should be inserted after docstring and imports
    assert "import pytest" in code
    assert code.index("import pytest") > code.index("'doc'")


def test_fixture_injector_inserts_fixture_after_pytest_import_and_adds_autouse_when_unittest():
    # module with pytest import
    imp_py = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
    module = cst.Module(body=[imp_py, cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Name("f")))])])
    # create a simple fixture node
    fn = cst.FunctionDef(
        name=cst.Name("a"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=[cst.Pass()]),
        decorators=[cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))],
    )
    # CollectorOutput with has_unittest_usage True to force autouse attach
    collector = CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={}, has_unittest_usage=True
    )
    res = fixture_injector.fixture_injector_stage(
        {"module": module, "fixture_nodes": [fn], "collector_output": collector}
    )
    new_mod = res["module"]
    code = new_mod.code
    # fixture should be present
    assert "def a" in code
    # autouse attach fixture name should be present
    assert "_attach_to_instance" in code
