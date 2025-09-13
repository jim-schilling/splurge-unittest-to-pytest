import libcst as cst

from splurge_unittest_to_pytest.converter.placement import insert_fixtures_into_module


def test_insert_fixtures_after_imports():
    module = cst.Module(
        body=[
            cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])]),
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Call(func=cst.Name("setup"), args=[]))]),
        ]
    )

    fixture_func = cst.FunctionDef(
        name=cst.Name("my_fixture"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )

    new_mod = insert_fixtures_into_module(module, {"my_fixture": fixture_func})
    # expecting module body to have import, then fixture, then setup call
    assert any(isinstance(n, cst.FunctionDef) for n in new_mod.body)
