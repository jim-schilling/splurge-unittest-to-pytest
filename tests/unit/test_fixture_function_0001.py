from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.converter.fixture_function import create_fixture_function


def test_create_fixture_function_basic_structure() -> None:
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    fn = create_fixture_function("my_fixture", body, decorator)
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "my_fixture"
    assert isinstance(fn.body, cst.IndentedBlock)
    assert len(fn.decorators) == 1
    assert isinstance(fn.decorators[0], cst.Decorator)
    # params should be empty
    assert len(fn.params.params) == 0
