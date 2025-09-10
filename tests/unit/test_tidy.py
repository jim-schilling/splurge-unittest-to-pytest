import libcst as cst
from splurge_unittest_to_pytest.stages.tidy import tidy_stage


def make_fixture(name: str) -> cst.FunctionDef:
    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))])])
    return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=body, decorators=[decorator])


def test_tidy_inserts_emptyline_after_fixtures():
    src = 'import pytest\n\n'
    module = cst.parse_module(src)
    fixtures = [make_fixture("a"), make_fixture("b")]
    # create module with fixtures followed by class
    new_body = list(module.body) + fixtures + [cst.ClassDef(name=cst.Name("A"), body=cst.IndentedBlock(body=[cst.Pass()]))]
    mod = module.with_changes(body=new_body)
    res = tidy_stage({"module": mod})
    new_mod = res.get("module")
    # find EmptyLine in body
    has_empty = any(isinstance(s, cst.EmptyLine) for s in new_mod.body)
    assert has_empty
