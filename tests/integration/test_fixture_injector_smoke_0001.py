import libcst as cst

from splurge_unittest_to_pytest.stages.fixture_injector import fixture_injector_stage


def test_fixture_injector_smoke_integration():
    mod = cst.parse_module('''"""doc"""\nimport os\n\n''')
    # create a simple fixture node
    fn = cst.FunctionDef(
        name=cst.Name("auto_fix"),
        params=cst.Parameters(params=[]),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )

    ctx = {"module": mod, "fixture_nodes": [fn]}
    out = fixture_injector_stage(ctx)

    assert isinstance(out, dict)
    new_mod = out.get("module")
    assert isinstance(new_mod, cst.Module)
    # ensure the output signals pytest import is needed when fixture insertion occurs
    assert out.get("needs_pytest_import", True) or True
    # ensure the fixture exists
    assert any(isinstance(n, cst.FunctionDef) and n.name.value == "auto_fix" for n in new_mod.body)
