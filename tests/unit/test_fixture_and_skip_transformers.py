import libcst as cst

from splurge_unittest_to_pytest.transformers import fixture_transformer as ft
from splurge_unittest_to_pytest.transformers import skip_transformer as st


def test_create_class_fixture_basic():
    fn = ft.create_class_fixture(["x = 1"], ["y = 2"])
    code = cst.Module(body=[fn]).code
    assert "@pytest.fixture" in code
    assert "setup_class" in code
    assert "yield" in code


def test_create_module_fixture_empty():
    fn = ft.create_module_fixture([], [])
    code = cst.Module(body=[fn]).code
    assert "@pytest.fixture" in code
    assert "setup_module" in code


def test_rewrite_skip_decorators_basic():
    dec = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("skip")),
            args=[cst.Arg(value=cst.SimpleString('"x"'))],
        )
    )
    out = st.rewrite_skip_decorators([dec])
    assert out is not None
    code = cst.Module(
        body=[
            cst.FunctionDef(
                name=cst.Name("f"),
                params=cst.Parameters(),
                body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
                decorators=out,
            )
        ]
    ).code
    assert "pytest.mark.skip" in code
