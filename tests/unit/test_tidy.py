import libcst as cst
from typing import cast, Sequence
from splurge_unittest_to_pytest.stages.tidy import tidy_stage


def make_fixture(name: str) -> cst.FunctionDef:
    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))])])
    return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=body, decorators=[decorator])


def test_tidy_inserts_emptyline_after_fixtures() -> None:
    src = 'import pytest\n\n'
    module = cst.parse_module(src)
    fixtures: list[cst.FunctionDef] = [make_fixture("a"), make_fixture("b")]
    # create module with fixtures followed by class
    # Use a SimpleStatementLine containing Pass so the class body conforms to
    # libcst's BaseSmallStatement expectations for module bodies.
    class_block = cst.ClassDef(
        name=cst.Name("A"),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )
    # module.body is a Sequence[cst.BaseSmallStatement] but we construct a
    # mixed list for test purposes — cast at the call site to satisfy mypy.
    new_body = list(module.body) + fixtures + [class_block]
    mod = module.with_changes(body=cast(Sequence[cst.BaseSmallStatement], new_body))
    res = tidy_stage({"module": mod})
    new_mod = cast(cst.Module, res.get("module"))
    # find EmptyLine in body
    has_empty = any(isinstance(s, cst.EmptyLine) for s in new_mod.body)
    assert has_empty
