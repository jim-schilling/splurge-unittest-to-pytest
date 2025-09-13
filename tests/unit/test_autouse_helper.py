from splurge_unittest_to_pytest.converter.autouse import (
    build_attach_to_instance_fixture,
    insert_attach_fixture_into_module,
)
import libcst as cst


def test_build_attach_fixture_empty():
    func = build_attach_to_instance_fixture({})
    assert isinstance(func, cst.FunctionDef)
    assert func.name.value == "_attach_to_instance"


def test_insert_attach_fixture_into_module():
    module = cst.parse_module("import pytest\n\n")
    func = build_attach_to_instance_fixture(
        {"res": cst.FunctionDef(name=cst.Name("res"), params=cst.Parameters(), body=cst.IndentedBlock(body=[]))}
    )
    new_mod = insert_attach_fixture_into_module(module, func)
    # Ensure the function appears in module body
    assert any(isinstance(s, cst.FunctionDef) and s.name.value == "_attach_to_instance" for s in new_mod.body)
