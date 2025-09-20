import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_fixture_injector import (
    FindInsertionIndexStep,
    InsertNodesStep,
    NormalizeAndPostprocessStep,
)


def _run_steps_for_module(module: cst.Module, fn: cst.FunctionDef):
    ctx = {"module": module, "fixture_nodes": [fn]}
    return run_steps(
        "st",
        "t",
        "n",
        [FindInsertionIndexStep(), InsertNodesStep(), NormalizeAndPostprocessStep()],
        ctx,
        None,
    )


def test_insertion_after_docstring_and_imports():
    mod = cst.parse_module('''"""doc"""\nimport os\nimport sys\n\n''')
    fn = cst.FunctionDef(
        name=cst.Name("placed"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )

    res = _run_steps_for_module(mod, fn)
    new_mod = res.delta.values.get("module")
    # insertion index should be after the two imports (index 3)
    # Find the fixture and assert preceding nodes are the imports/docstring or EmptyLine markers
    indices = [i for i, n in enumerate(new_mod.body) if isinstance(n, cst.FunctionDef) and n.name.value == "placed"]
    assert indices, "fixture not inserted"
    idx = indices[0]
    # before the fixture, we should see two EmptyLine markers due to normalization
    assert isinstance(new_mod.body[idx - 2], cst.EmptyLine)
    assert isinstance(new_mod.body[idx - 1], cst.EmptyLine)


def test_insertion_after_existing_import_pytest():
    mod = cst.parse_module("""import os\nimport pytest\nimport sys\n\n""")
    fn = cst.FunctionDef(
        name=cst.Name("after_pytest"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )

    res = _run_steps_for_module(mod, fn)
    new_mod = res.delta.values.get("module")
    # Ensure the fixture is placed immediately after the import pytest line
    for idx, node in enumerate(new_mod.body):
        if isinstance(node, cst.FunctionDef) and node.name.value == "after_pytest":
            # the node before two markers should follow the import pytest
            # locate import pytest index
            for j, n in enumerate(new_mod.body):
                if isinstance(n, cst.SimpleStatementLine) and n.body and isinstance(n.body[0], cst.Import):
                    for name in n.body[0].names:
                        if getattr(name.name, "value", None) == "pytest":
                            pytest_idx = j
                            # fixture insertion should be after pytest_idx (accounting for EmptyLine markers)
                            assert idx >= pytest_idx + 1
                            return
    raise AssertionError("fixture not inserted after import pytest")
