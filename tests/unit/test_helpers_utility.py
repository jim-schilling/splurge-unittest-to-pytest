import pytest

from splurge_unittest_to_pytest.helpers.utility import (
    safe_replace_one_arg_call,
    safe_replace_two_arg_call,
    split_two_args_balanced,
)


def test_split_two_args_balanced_simple():
    assert split_two_args_balanced("a, b") == ("a", "b")


def test_split_two_args_balanced_nested():
    assert split_two_args_balanced("func(1, 2), [3, 4]") == ("func(1, 2)", "[3, 4]")


def test_split_two_args_balanced_with_quotes_and_commas():
    assert split_two_args_balanced('"a,comma", b') == ('"a,comma"', "b")


def test_split_two_args_balanced_no_split_returns_none():
    assert split_two_args_balanced("just_one_arg") is None


def test_safe_replace_one_arg_call_basic():
    code = "self.assertTrue(x > 0)\nother()"
    out = safe_replace_one_arg_call(code, "assertTrue", lambda a: f"assert {a}")
    assert "assert x > 0" in out


def test_safe_replace_two_arg_call_basic():
    code = "self.assertEqual(a, b)\nself.assertEqual(c, d)"
    out = safe_replace_two_arg_call(code, "assertEqual", lambda a, b: f"assert {a} == {b}")
    assert out.count("assert ") == 2


def test_safe_replace_handles_escaped_parentheses():
    code = 'self.assertTrue("foo(\\)bar")'
    out = safe_replace_one_arg_call(code, "assertTrue", lambda a: f"assert {a}")
    assert 'assert "foo(\\)bar"' in out


def test_split_two_args_balanced_single_quoted_comma():
    assert split_two_args_balanced("'a, b', c") == ("'a, b'", "c")


def test_safe_replace_two_arg_call_no_replacement_for_single_arg():
    code = "self.assertEqual(single_arg)\nrest()"
    out = safe_replace_two_arg_call(code, "assertEqual", lambda a, b: f"assert {a} == {b}")
    # Should not replace because call only has one arg (split_two_args_balanced returns None)
    assert "self.assertEqual(single_arg)" in out


def test_safe_replace_two_arg_call_escaped_quotes_and_multiple():
    code = 'pre\nself.assertEqual("a,\\"x\\"", b)\nmid\nself.assertEqual(foo(1,2), bar)\n'
    out = safe_replace_two_arg_call(code, "assertEqual", lambda a, b: f"assert {a} == {b}")
    # Both occurrences should be replaced into assert expressions
    assert out.count("assert ") >= 2


def test_safe_replace_one_arg_call_unbalanced_no_change():
    # missing closing parenthesis -> depth != 0 branch should keep original slice
    code = "start\nself.assertTrue((a > 0\nend"
    out = safe_replace_one_arg_call(code, "assertTrue", lambda a: f"assert {a}")
    assert "self.assertTrue((a > 0" in out
