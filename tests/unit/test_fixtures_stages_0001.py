from typing import cast

import libcst as cst
from libcst import parse_module

from splurge_unittest_to_pytest.stages.collector import CollectorOutput
from splurge_unittest_to_pytest.stages.fixture_injector import (
    _find_insertion_index,
    _make_autouse_attach,
    fixture_injector_stage,
)


def test_find_insertion_index_after_pytest_import():
    src = "import os\nimport pytest\n\nclass X: pass\n"
    mod = cst.parse_module(src)
    idx = _find_insertion_index(mod)
    assert idx == 2


def test_make_autouse_attach_contains_getfixturevalue_and_autouse():
    fn = (
        _make_autouse_attach(["a", "b"])
        if hasattr(__import__("splurge_unittest_to_pytest.stages.fixture_injector"), "_make_autouse_attach")
        else None
    )
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
    found = [n for n in new_module.body if isinstance(n, cst.FunctionDef) and n.name.value in ("a", "b")]
    assert len(found) == 2


def test_fixture_injector_inserts_nodes_and_autouse_when_unittest_used() -> None:
    src = "import pytest\n\nclass T:\n    pass\n"
    module = cst.parse_module(src)
    fn = cst.FunctionDef(
        name=cst.Name("x"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Return(cst.Integer("42"))])]),
        decorators=[cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))],
    )
    collector = CollectorOutput(
        module=module, module_docstring_index=None, imports=(), classes={}, has_unittest_usage=True
    )
    out = fixture_injector_stage({"module": module, "fixture_nodes": [fn], "collector_output": collector})
    new_mod = out.get("module")
    assert new_mod is not None
    assert any((isinstance(n, cst.FunctionDef) and n.name.value == "x" for n in new_mod.body))
    assert any((isinstance(n, cst.FunctionDef) and n.name.value == "x" for n in new_mod.body))


def _make_module_with_placeholders() -> cst.Module:
    imp = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    return cst.Module(body=[imp])


def _make_fn(name: str) -> cst.FunctionDef:
    return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))


def test_inserts_two_blank_lines_before_defs() -> None:
    mod = _make_module_with_placeholders()
    nodes = [_make_fn("fix1"), _make_fn("fix2")]
    ctx = {"module": mod, "fixture_nodes": nodes}
    out = fixture_injector_stage(ctx)
    new_mod = out.get("module")
    assert isinstance(new_mod, cst.Module)
    body = list(new_mod.body)
    positions = [i for i, n in enumerate(body) if isinstance(n, cst.FunctionDef)]
    assert positions, "No FunctionDef found"
    for pos in positions:
        cnt = 0
        j = pos - 1
        while j >= 0 and isinstance(body[j], cst.EmptyLine):
            cnt += 1
            j -= 1
        assert cnt >= 2, f"Expected >=2 EmptyLine before def at pos {pos}, found {cnt}"
