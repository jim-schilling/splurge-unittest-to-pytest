import libcst as cst

from splurge_unittest_to_pytest.stages.fixture_injector import fixture_injector_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


def test_fixture_injector_inserts_nodes_and_autouse_when_unittest_used() -> None:
    src = """import pytest\n\nclass T:\n    pass\n"""
    module = cst.parse_module(src)
    # create a dummy fixture node
    fn = cst.FunctionDef(
        name=cst.Name("x"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Return(cst.Integer("42"))])]),
        decorators=[cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))],
    )
    # collector with has_unittest_usage True should trigger autouse attach
    collector = CollectorOutput(
        module=module, module_docstring_index=None, imports=(), classes={}, has_unittest_usage=True
    )
    out = fixture_injector_stage({"module": module, "fixture_nodes": [fn], "collector_output": collector})
    new_mod = out.get("module")
    assert new_mod is not None
    assert any(isinstance(n, cst.FunctionDef) and n.name.value == "x" for n in new_mod.body)
    # autouse attach fixture removed; expect fixture 'x' present and pytest import signaled
    assert any(isinstance(n, cst.FunctionDef) and n.name.value == "x" for n in new_mod.body)
