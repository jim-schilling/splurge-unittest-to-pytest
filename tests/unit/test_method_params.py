import libcst as cst

from splurge_unittest_to_pytest.converter.method_params import (
    should_remove_first_param,
    remove_method_self_references,
)


def _parse_func(src: str) -> cst.FunctionDef:
    mod = cst.parse_module(src)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found: cst.FunctionDef | None = None

        def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
            if self.found is None:
                self.found = node

    finder = Finder()
    mod.visit(finder)
    if finder.found is None:
        raise RuntimeError("No FunctionDef found in source")
    return finder.found


def test_should_remove_for_instance_method():
    fn = _parse_func("def test(self):\n    pass")
    assert should_remove_first_param(fn)


def test_should_not_remove_for_staticmethod():
    fn = _parse_func("@staticmethod\ndef test():\n    pass")
    assert not should_remove_first_param(fn)


def test_should_remove_for_classmethod():
    fn = _parse_func("@classmethod\ndef test(cls):\n    pass")
    assert should_remove_first_param(fn)


def test_remove_method_self_references_removes_param_and_references():
    fn = _parse_func("def test(self):\n    self.x = 1\n    return self.x")
    new_params, new_body = remove_method_self_references(fn)
    assert all(p.name.value != "self" for p in new_params)
    code = cst.Module([]).code_for_node(new_body)
    assert "self" not in code
