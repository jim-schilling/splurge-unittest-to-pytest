import libcst as cst

from splurge_unittest_to_pytest.converter import helpers
from splurge_unittest_to_pytest.converter.call_utils import is_self_call


def test_is_self_call_positive():
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("do_something")),
        args=[cst.Arg(value=cst.Integer("1"))],
    )
    res = is_self_call(call)
    assert res is not None
    name, args = res
    assert name == "do_something"
    assert len(args) == 1


def test_is_self_call_negative():
    call = cst.Call(func=cst.Name("do_something_else"), args=[])
    assert is_self_call(call) is None


def test_normalize_method_name_handles_camel_and_snake():
    assert helpers.normalize_method_name("assertRaisesRegex") == "assert_raises_regex"
    assert helpers.normalize_method_name("testMethodName") == "test_method_name"
    assert helpers.normalize_method_name("already_snake") == "already_snake"


def test_parse_method_patterns_handles_none_commas_and_duplicates():
    assert helpers.parse_method_patterns(None) == []
    assert helpers.parse_method_patterns(()) == []
    assert helpers.parse_method_patterns(["a,b, c", "d"]) == ["a", "b", "c", "d"]
    assert helpers.parse_method_patterns(["x,x,y"]) == ["x", "y"]


def test_self_reference_remover_rewrites_attribute_accesses_in_expr_and_module():
    expr = cst.parse_expression("self.x + cls.y + other.z")
    new_expr = expr.visit(helpers.SelfReferenceRemover())
    code_expr = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=new_expr)])]).code
    assert "self." not in code_expr and "cls." not in code_expr
    module_src = "def test(self):\n    return self.value\n"
    module = cst.parse_module(module_src)
    new_mod = module.visit(helpers.SelfReferenceRemover())
    assert "return value" in new_mod.code


def test_has_meaningful_changes_detects_formatting_and_semantic_differences():
    orig = "def f():\n    return 1\n"
    assert not helpers.has_meaningful_changes(orig, orig)
    conv_fmt = "def f():\n\n    return 1\n"
    assert not helpers.has_meaningful_changes(orig, conv_fmt)
    conv_ast = "def f():\n    return (1)\n"
    assert not helpers.has_meaningful_changes(orig, conv_ast)
    conv_change = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv_change)


def test_core_exports():
    assert hasattr(helpers, "SelfReferenceRemover")
    assert hasattr(helpers, "normalize_method_name")


def test_parse_method_patterns_various():
    assert helpers.parse_method_patterns(("setUp", "beforeAll")) == ["setUp", "beforeAll"]
    assert helpers.parse_method_patterns(("  setUp  , beforeAll  ",)) == ["setUp", "beforeAll"]
    assert helpers.parse_method_patterns(("a,a,b",)) == ["a", "b"]
    assert helpers.parse_method_patterns(None) == []


def test_has_meaningful_changes_formatting_only():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 1\n"
    assert not helpers.has_meaningful_changes(orig, conv)


def test_has_meaningful_changes_real_change():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv)


def test_normalize_method_name_edge_cases():
    assert helpers.normalize_method_name("HTTPResponseCode") == "http_response_code"
    assert helpers.normalize_method_name("setup_class") == "setup_class"
    assert helpers.normalize_method_name("test123Case") == "test123_case"
