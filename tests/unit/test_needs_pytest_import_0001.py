import libcst as cst

from splurge_unittest_to_pytest.stages.steps_fixture_injector import (
    FindInsertionIndexStep,
    InsertNodesStep,
    NormalizeAndPostprocessStep,
)
from splurge_unittest_to_pytest.stages.steps import run_steps


def test_needs_pytest_import_propagation_from_steps():
    mod = cst.parse_module("""import os\n\n""")
    fn = cst.FunctionDef(
        name=cst.Name("fix"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )

    ctx = {"module": mod, "fixture_nodes": [fn]}
    res = run_steps(
        "st",
        "t",
        "n",
        [FindInsertionIndexStep(), InsertNodesStep(), NormalizeAndPostprocessStep()],
        ctx,
        None,
    )

    assert res.errors == []
    assert res.delta.values.get("needs_pytest_import") is True
