import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_fixture_injector import (
    FindInsertionIndexStep,
    InsertNodesStep,
    NormalizeAndPostprocessStep,
)


def test_insert_empty_lines_with_fixture():
    # Module with a docstring and one import
    mod = cst.parse_module('''"""doc"""\nimport os\n\n''')
    # Create a simple fixture function
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
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)

    # Find the index of the inserted fixture and assert surrounding nodes include EmptyLine
    for idx, node in enumerate(new_mod.body):
        if isinstance(node, cst.FunctionDef) and node.name.value == "fix":
            # previous two nodes should be EmptyLine markers
            assert idx >= 2
            assert isinstance(new_mod.body[idx - 2], cst.EmptyLine)
            assert isinstance(new_mod.body[idx - 1], cst.EmptyLine)
            break
    else:
        raise AssertionError("Inserted fixture not found")
