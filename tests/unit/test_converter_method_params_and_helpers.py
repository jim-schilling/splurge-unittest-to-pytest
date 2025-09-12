import libcst as cst

from splurge_unittest_to_pytest.converter import method_params
from splurge_unittest_to_pytest.converter import helpers


def make_func(src: str) -> cst.FunctionDef:
    mod = cst.parse_module(src)
    # assume the first top-level statement is a simple function def
    for node in mod.body:
        if isinstance(node, cst.FunctionDef):
            return node
        if isinstance(node, cst.SimpleStatementLine) and node.body:
            first = node.body[0]
            if isinstance(first, cst.FunctionDef):
                return first
    raise RuntimeError("no function found")


def test_should_remove_first_param_self():
    src = "def f(self, x):\n    return self.x + x\n"
    fn = make_func(src)
    assert method_params.should_remove_first_param(fn) is True


def test_should_remove_first_param_classmethod():
    src = "@classmethod\ndef f(cls, x):\n    return cls.x + x\n"
    fn = make_func(src)
    assert method_params.should_remove_first_param(fn) is True


def test_should_not_remove_first_param_staticmethod():
    src = "@staticmethod\ndef f(x):\n    return x\n"
    fn = make_func(src)
    assert method_params.should_remove_first_param(fn) is False


def test_remove_method_self_references_removes_self_attr():
    src = "def f(self, x):\n    return self.value + x\n"
    fn = make_func(src)
    new_params, new_body = method_params.remove_method_self_references(fn)
    # first param removed
    assert len(new_params) == 1 and new_params[0].name.value == "x"
    # body should have attributes rewritten (self.value -> value)
    assert isinstance(new_body, cst.BaseSuite)
    assert "value" in cst.Module(body=[new_body]).code


def test_normalize_method_name():
    assert helpers.normalize_method_name("camelCase") == "camel_case"
    assert helpers.normalize_method_name("HTTPRequest") == "http_request"


def test_parse_method_patterns():
    assert helpers.parse_method_patterns(None) == []
    assert helpers.parse_method_patterns(["one,two", "three"]) == ["one", "two", "three"]
    assert helpers.parse_method_patterns(["dup,dup"]) == ["dup"]


def test_has_meaningful_changes_ast_vs_text():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 1\n"
    assert helpers.has_meaningful_changes(orig, conv) is False

    conv2 = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv2) is True
