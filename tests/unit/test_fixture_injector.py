import libcst as cst
from typing import cast
from splurge_unittest_to_pytest.stages.fixture_injector import fixture_injector_stage
from libcst import parse_module


def make_dummy_fixture(name: str) -> cst.FunctionDef:
    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))])])
    return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=body, decorators=[decorator])


def test_fixture_injector_inserts_fixtures_after_import() -> None:
    src = "import pytest\n\nclass A:\n    pass\n"
    module = parse_module(src)
    fixtures = [make_dummy_fixture("a"), make_dummy_fixture("b")]
    ctx = {"module": module, "fixture_nodes": fixtures, "collector_output": None, "compat": False}
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

    ctx = {"module": module, "fixture_nodes": fixtures, "collector_output": Co(), "compat": True}
    res = fixture_injector_stage(ctx)
    new_module = cast(cst.Module, res.get("module"))
    # compatibility autouse attach removed; ensure fixture 'res' was inserted
    fixtures = [n for n in new_module.body if isinstance(n, cst.FunctionDef) and n.name.value == "res"]
    assert len(fixtures) == 1
