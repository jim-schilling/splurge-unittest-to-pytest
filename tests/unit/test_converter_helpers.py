import libcst as cst
from splurge_unittest_to_pytest.converter import helpers


def test_normalize_method_name_snake_and_camel():
    assert helpers.normalize_method_name("testMethodName") == "test_method_name"
    assert helpers.normalize_method_name("already_snake") == "already_snake"


def test_parse_method_patterns_empty_and_commas():
    assert helpers.parse_method_patterns(None) == []
    assert helpers.parse_method_patterns(()) == []
    assert helpers.parse_method_patterns(["a,b, c", "d"]) == ["a", "b", "c", "d"]
    # duplicates preserved only once
    assert helpers.parse_method_patterns(["x,x,y"]) == ["x", "y"]


def test_self_reference_remover_replaces_self_attr():
    code = "def test(self):\n    return self.value\n"
    module = cst.parse_module(code)
    new = module.visit(helpers.SelfReferenceRemover())
    # the returned module should have 'return value' not 'return self.value'
    assert "return value" in new.code


def test_has_meaningful_changes_detects_ast_and_formatting_cases():
    orig = "def f():\n    return 1\n"
    # identical code -> no meaningful changes
    assert not helpers.has_meaningful_changes(orig, orig)

    # formatting-only difference (extra blank lines) should be treated as no meaningful change
    conv_fmt = "def f():\n\n    return 1\n"
    assert not helpers.has_meaningful_changes(orig, conv_fmt)

    # AST-equal but text-different (same AST) -> no meaningful change
    conv_ast = "def f():\n    return (1)\n"
    assert not helpers.has_meaningful_changes(orig, conv_ast)

    # real change -> detected
    conv_change = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv_change)

# ...existing tests above...
