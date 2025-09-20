import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_fixture_injector import (
    FindInsertionIndexStep,
    InsertNodesStep,
    NormalizeAndPostprocessStep,
)


def make_simple_module():
    return cst.parse_module(
        """
"""
        + "\nimport os\n\n"
    )


def test_find_and_insert_fixture():
    mod = cst.parse_module('''"""doc"""\nimport os\n\n''')
    # create a simple fixture node
    fn = cst.FunctionDef(
        name=cst.Name("r"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )
    context = {"module": mod, "fixture_nodes": [fn]}
    res = run_steps(
        "st", "t", "n", [FindInsertionIndexStep(), InsertNodesStep(), NormalizeAndPostprocessStep()], context, None
    )
    assert res.errors == []
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # fixture function should be present
    assert any(isinstance(n, cst.FunctionDef) and n.name.value == "r" for n in new_mod.body)


def test_normalize_preserves_spacing_and_rewrites_self_attr():
    mod = cst.parse_module("""import pytest\n\n\n\n""")
    fn = cst.FunctionDef(
        name=cst.Name("r"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(
            body=[
                cst.SimpleStatementLine(
                    body=[cst.Expr(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")))]
                )
            ]
        ),
    )
    context = {"module": mod, "fixture_nodes": [fn]}
    res = run_steps(
        "st", "t", "n", [FindInsertionIndexStep(), InsertNodesStep(), NormalizeAndPostprocessStep()], context, None
    )
    new_mod = res.delta.values.get("module")
    # Assert the inserted fixture exists and the self.x was rewritten to x inside fixture body
    found = False
    for n in new_mod.body:
        if isinstance(n, cst.FunctionDef) and n.name.value == "r":
            found = True
            # Render the FunctionDef into a Module to obtain source text
            fn_src = cst.Module(body=[n]).code
            assert "self.x" not in fn_src
            assert "x" in fn_src
    assert found
