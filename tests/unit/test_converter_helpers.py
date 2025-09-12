import libcst as cst

from splurge_unittest_to_pytest.converter.helpers import (
    normalize_method_name,
    parse_method_patterns,
    SelfReferenceRemover,
    has_meaningful_changes,
)


def test_normalize_method_name():
    assert normalize_method_name("assertEqual") == "assert_equal"
    assert normalize_method_name("camelCaseTest") == "camel_case_test"
    assert normalize_method_name("lowercase") == "lowercase"


def test_parse_method_patterns_empty():
    assert parse_method_patterns(None) == []
    assert parse_method_patterns([]) == []


def test_parse_method_patterns_commas_and_duplicates():
    patterns = parse_method_patterns(("testOne,testTwo", " testTwo ", "testThree", ""))
    assert patterns == ["testOne", "testTwo", "testThree"]


def test_self_reference_remover_replaces_self_attr():
    src = "def f(self):\n    return self.x + cls.y\n"
    mod = cst.parse_module(src)
    transformer = SelfReferenceRemover(param_names={"self", "cls"})
    new = mod.visit(transformer)
    code = new.code
    # 'self.x' becomes 'x' and 'cls.y' becomes 'y'
    assert "self.x" not in code
    assert "cls.y" not in code
    assert "x" in code
    assert "y" in code


def test_has_meaningful_changes_detects_formatting_only():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n\n    return 1\n"
    # formatting-only should return False
    assert has_meaningful_changes(orig, conv) is False


def test_has_meaningful_changes_detects_semantic_change():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 2\n"
    assert has_meaningful_changes(orig, conv) is True
