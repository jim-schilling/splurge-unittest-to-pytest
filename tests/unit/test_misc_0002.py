import libcst as cst
from tests.unit.helpers.autouse_helpers import make_autouse_attach, insert_attach_fixture_into_module

DOMAINS = ["misc"]


def test_build_attach_fixture_empty():
    func = make_autouse_attach({})
    assert isinstance(func, cst.FunctionDef)
    assert func.name.value == "_attach_to_instance"


def test_insert_attach_fixture_into_module():
    module = cst.parse_module("import pytest\n\n")
    func = make_autouse_attach(
        {"res": cst.FunctionDef(name=cst.Name("res"), params=cst.Parameters(), body=cst.IndentedBlock(body=[]))}
    )
    # Use the insertion helper that accepts an already-built FunctionDef
    new_mod = insert_attach_fixture_into_module(module, func)
    # Ensure the function appears in module body
    assert any(isinstance(s, cst.FunctionDef) and s.name.value == "_attach_to_instance" for s in new_mod.body)
