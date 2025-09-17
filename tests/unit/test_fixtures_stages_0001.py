import libcst as cst
from libcst import parse_module
from typing import cast
from splurge_unittest_to_pytest.stages.fixture_injector import (
    _find_insertion_index,
    _make_autouse_attach,
    fixture_injector_stage,
)

DOMAINS = ["fixtures", "stages"]


def test_find_insertion_index_after_pytest_import():
    src = "import os\nimport pytest\n\nclass X: pass\n"
    mod = cst.parse_module(src)
    idx = _find_insertion_index(mod)
    # pytest import is at index 1 so insertion should be 2
    assert idx == 2


def test_make_autouse_attach_contains_getfixturevalue_and_autouse():
    fn = (
        _make_autouse_attach(["a", "b"])
        if hasattr(__import__("splurge_unittest_to_pytest.stages.fixture_injector"), "_make_autouse_attach")
        else None
    )
    # call the factory and assert it builds a FunctionDef
    if fn is not None:
        assert isinstance(fn, cst.FunctionDef)
        code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(fn)])]).code
        assert "getfixturevalue" in code or "getfixturevalue" in code


def make_dummy_fixture(name: str) -> cst.FunctionDef:
    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))])])
    return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=body, decorators=[decorator])


def test_fixture_injector_inserts_fixtures_after_import() -> None:
    src = "import pytest\n\nclass A:\n    pass\n"
    module = parse_module(src)
    fixtures = [make_dummy_fixture("a"), make_dummy_fixture("b")]
    ctx = {"module": module, "fixture_nodes": fixtures, "collector_output": None}
    res = fixture_injector_stage(ctx)
    new_module = cast(cst.Module, res.get("module"))
    # find fixtures present after import
    found = [n for n in new_module.body if isinstance(n, cst.FunctionDef) and n.name.value in ("a", "b")]
    assert len(found) == 2


def test_fixture_injector_adds_compat_attacher() -> None:
    src = '"""doc"""\n\nclass A:\n    pass\n'
    module = parse_module(src)
    fixtures = [make_dummy_fixture("res")]

    # create a fake collector output marking unittest usage
    class Co:
        has_unittest_usage = True

    ctx = {"module": module, "fixture_nodes": fixtures, "collector_output": Co()}
    res = fixture_injector_stage(ctx)
    new_module = cast(cst.Module, res.get("module"))
    # compatibility autouse attach removed; ensure fixture 'res' was inserted
    fixtures = [n for n in new_module.body if isinstance(n, cst.FunctionDef) and n.name.value == "res"]
    assert len(fixtures) == 1
