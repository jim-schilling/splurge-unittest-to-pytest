import libcst as cst

from splurge_unittest_to_pytest.converter import method_params
from splurge_unittest_to_pytest.converter import params as conv_params
from splurge_unittest_to_pytest.converter.method_params import remove_method_self_references, should_remove_first_param
from splurge_unittest_to_pytest.converter.params import append_fixture_params


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
    assert all((p.name.value != "self" for p in new_params))
    code = cst.Module([]).code_for_node(new_body)
    assert "self" not in code


def test_append_fixture_params_preserves_existing():
    existing = cst.Parameters(params=[cst.Param(name=cst.Name("a"))])
    out = append_fixture_params(existing, ["f1", "f2"])
    names = [p.name.value for p in out.params]
    assert names == ["a", "f1", "f2"]


def _make_func(src: str) -> cst.FunctionDef:
    module = cst.parse_module(src)
    for node in module.body:
        if isinstance(node, cst.FunctionDef):
            return node
        if isinstance(node, cst.SimpleStatementLine) and isinstance(node.body[0], cst.FunctionDef):
            return node.body[0]
    raise AssertionError("no function found")


def test_should_remove_first_param_simple():
    src = "def test_it(self):\n    return 1\n"
    fn = _make_func(src)
    assert method_params.should_remove_first_param(fn)


def test_should_not_remove_staticmethod():
    src = "@staticmethod\ndef f():\n    return 1\n"
    fn = _make_func(src)
    assert not method_params.should_remove_first_param(fn)


def test_remove_method_self_references_removes_param_and_rewrites_body():
    src = "def test_x(self):\n    return self.value\n"
    fn = _make_func(src)
    new_params, new_body = method_params.remove_method_self_references(fn)
    assert all((p.name.value != "self" for p in new_params))
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=new_body)])]).code
    assert "self" not in code


def test_get_fixture_param_names_order():
    a = cst.parse_module("def a():\n    pass\n").body[0]
    b = cst.parse_module("def b():\n    pass\n").body[0]
    fixtures = {"a": a, "b": b}
    names = conv_params.get_fixture_param_names(fixtures)
    assert set(names) == {"a", "b"}


def test_make_fixture_params_creates_params():
    p = conv_params.make_fixture_params(["fx", "fy"])
    assert isinstance(p, cst.Parameters)
    assert [param.name.value for param in p.params] == ["fx", "fy"]


def test_append_fixture_params_preserves_existing__01():
    existing = cst.Parameters(params=[cst.Param(name=cst.Name("x"))])
    p = conv_params.append_fixture_params(existing, ["fx"])
    assert [param.name.value for param in p.params] == ["x", "fx"]
