import libcst as cst
from typing import cast, Sequence
from splurge_unittest_to_pytest.stages.tidy import tidy_stage


def make_fixture(name: str) -> cst.FunctionDef:
    decorator = cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Return(cst.Name("None"))])])
    return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=body, decorators=[decorator])


def test_tidy_inserts_emptyline_after_fixtures() -> None:
    src = "import pytest\n\n"
    module = cst.parse_module(src)
    fixtures: list[cst.FunctionDef] = [make_fixture("a"), make_fixture("b")]
    class_block = cst.ClassDef(
        name=cst.Name("A"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    new_body = list(module.body) + fixtures + [class_block]
    mod = module.with_changes(body=cast(Sequence[cst.BaseSmallStatement], new_body))
    res = tidy_stage({"module": mod})
    new_mod = cast(cst.Module, res.get("module"))
    has_empty = any((isinstance(s, cst.EmptyLine) for s in new_mod.body))
    assert has_empty


def test_tidy_adds_self_to_test_methods_without_params() -> None:
    src = "class TestA:\n    def test_one(self):\n        pass\n\nclass B:\n    def test_two():\n        pass\n"
    module = cst.parse_module(src)
    res = tidy_stage({"module": module})
    new_mod = cast(cst.Module, res.get("module"))
    cls_b = next((s for s in new_mod.body if isinstance(s, cst.ClassDef) and s.name.value == "B"), None)
    assert isinstance(cls_b, cst.ClassDef)
    func = next((m for m in cls_b.body.body if isinstance(m, cst.FunctionDef) and m.name.value == "test_two"), None)
    assert isinstance(func, cst.FunctionDef)
    assert len(func.params.params) == 1
    assert func.params.params[0].name.value == "self"


def test_tidy_keeps_existing_params_on_test_methods() -> None:
    src = "class C:\n    def test_with_param(x):\n        pass\n"
    module = cst.parse_module(src)
    res = tidy_stage({"module": module})
    new_mod = cast(cst.Module, res.get("module"))
    cls = next((s for s in new_mod.body if isinstance(s, cst.ClassDef) and s.name.value == "C"), None)
    assert isinstance(cls, cst.ClassDef)
    func = next(
        (m for m in cls.body.body if isinstance(m, cst.FunctionDef) and m.name.value == "test_with_param"), None
    )
    assert isinstance(func, cst.FunctionDef)
    assert len(func.params.params) == 1
    assert func.params.params[0].name.value == "x"
