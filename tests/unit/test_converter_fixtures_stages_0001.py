import libcst as cst

from splurge_unittest_to_pytest.converter.simple_fixture import create_simple_fixture
from splurge_unittest_to_pytest.stages.fixture_injector import _find_insertion_index, fixture_injector_stage


def test_create_simple_fixture_int():
    fn = create_simple_fixture("x", cst.Integer("1"))
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "x"
    assert fn.returns is not None


def test_find_insertion_index_after_import():
    module = cst.parse_module("import pytest\n\n")
    idx = _find_insertion_index(module)
    assert isinstance(idx, int)


def test_fixture_injector_stage_inserts_nodes():
    module = cst.parse_module("import os\n\n# module\n")
    fn = create_simple_fixture("a", cst.SimpleString("'ok'"))
    out = fixture_injector_stage({"module": module, "fixture_nodes": [fn]})
    assert "module" in out
    new_mod = out["module"]
    assert "def a(" in new_mod.code
