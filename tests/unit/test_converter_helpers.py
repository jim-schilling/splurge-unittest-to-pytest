import libcst as cst

from splurge_unittest_to_pytest.converter import helpers


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
    # expression case
    expr = cst.parse_expression("self.x + cls.y + other.z")
    new_expr = expr.visit(helpers.SelfReferenceRemover())
    code_expr = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=new_expr)])]).code
    assert "self." not in code_expr and "cls." not in code_expr

    # module case (ensure return statement is rewritten)
    module_src = "def test(self):\n    return self.value\n"
    module = cst.parse_module(module_src)
    new_mod = module.visit(helpers.SelfReferenceRemover())
    assert "return value" in new_mod.code


def test_has_meaningful_changes_detects_formatting_and_semantic_differences():
    orig = "def f():\n    return 1\n"
    # identical -> no change
    assert not helpers.has_meaningful_changes(orig, orig)

    # formatting-only difference -> no meaningful change
    conv_fmt = "def f():\n\n    return 1\n"
    assert not helpers.has_meaningful_changes(orig, conv_fmt)

    # AST-equal but text-different -> no meaningful change
    conv_ast = "def f():\n    return (1)\n"
    assert not helpers.has_meaningful_changes(orig, conv_ast)

    # real change -> detected
    conv_change = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv_change)
