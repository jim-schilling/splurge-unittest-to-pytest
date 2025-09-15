import libcst as cst

from splurge_unittest_to_pytest.converter import method_params

DOMAINS = ["core"]


def _make_func(src: str) -> cst.FunctionDef:
    module = cst.parse_module(src)
    # Grab the first function definition
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
    # params list should drop the 'self' param
    assert all(p.name.value != "self" for p in new_params)
    # body should no longer contain 'self.' when rendered
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=new_body)])]).code
    assert "self" not in code
