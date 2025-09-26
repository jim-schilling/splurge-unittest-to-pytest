"""Assertion transformation helpers extracted from unittest_transformer.

These functions perform CST-based conversion of unittest assertion calls
into equivalent pytest-style assertions or expressions. They are
extracted to keep `unittest_transformer.py` focused and allow reuse.
"""

import re

import libcst as cst

from ..helpers.utility import (
    safe_replace_one_arg_call,
    safe_replace_two_arg_call,
)


def transform_assert_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_true(node: cst.Call) -> cst.CSTNode:
    """Transform assertTrue to assert."""
    if len(node.args) >= 1:
        return cst.Assert(test=node.args[0].value)
    return node


def transform_assert_false(node: cst.Call) -> cst.CSTNode:
    """Transform assertFalse to assert not."""
    if len(node.args) >= 1:
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=node.args[0].value))
    return node


def transform_assert_is(node: cst.Call) -> cst.CSTNode:
    """Transform assertIs to assert is."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertNotEqual to assert !=."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsNot to assert is not."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_none(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsNone to assert <expr> is None."""
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not_none(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsNotNone to assert <expr> is not None."""
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_in(node: cst.Call) -> cst.CSTNode:
    """Transform assertNotIn to assert not in."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotIn(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_count_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertCountEqual(a, b) -> assert sorted(a) == sorted(b)."""
    if len(node.args) >= 2:
        left = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[0].value)])
        right = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[1].value)])
        comp = cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=right)])
        return cst.Assert(test=comp)
    return node


def transform_assert_regex(
    node: cst.Call, re_alias: str | None = None, re_search_name: str | None = None
) -> cst.CSTNode:
    """Transform assertRegex(a, pattern) -> assert re.search(pattern, a).

    This is a simple approximation and will require `re` to be available.
    """
    if len(node.args) >= 2:
        # If caller imported `search` directly (from re import search), use that name
        if re_search_name:
            func: cst.BaseExpression = cst.Name(value=re_search_name)
        else:
            re_name = re_alias or "re"
            func = cst.Attribute(value=cst.Name(value=re_name), attr=cst.Name(value="search"))

        call = cst.Call(
            func=func,
            args=[cst.Arg(value=node.args[1].value), cst.Arg(value=node.args[0].value)],
        )
        return cst.Assert(test=call)
    return node


def transform_assert_not_regex(
    node: cst.Call, re_alias: str | None = None, re_search_name: str | None = None
) -> cst.CSTNode:
    """Transform assertNotRegex(a, pattern) -> assert not re.search(pattern, a)."""
    if len(node.args) >= 2:
        if re_search_name:
            func: cst.BaseExpression = cst.Name(value=re_search_name)
        else:
            re_name = re_alias or "re"
            func = cst.Attribute(value=cst.Name(value=re_name), attr=cst.Name(value="search"))

        call = cst.Call(func=func, args=[cst.Arg(value=node.args[1].value), cst.Arg(value=node.args[0].value)])
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=call))
    return node


def transform_assert_in(node: cst.Call) -> cst.CSTNode:
    """Transform assertIn to assert in."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_raises(node: cst.Call) -> cst.CSTNode:
    """Transform assertRaises to pytest.raises context manager (approximate)."""
    if len(node.args) >= 2:
        exception_type = node.args[0].value
        code_to_test = node.args[1].value
        new_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises"))
        new_args = [
            cst.Arg(value=exception_type),
            cst.Arg(value=cst.Call(func=cst.Name(value="lambda"), args=[cst.Arg(value=code_to_test)])),
        ]
        return cst.Call(func=new_attr, args=new_args)
    return node


def transform_assert_dict_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertDictEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_list_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertListEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_set_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertSetEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_tuple_equal(node: cst.Call) -> cst.CSTNode:
    """Transform assertTupleEqual to assert ==."""
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_raises_regex(node: cst.Call) -> cst.CSTNode:
    """Transform assertRaisesRegex to pytest.raises with match (approximate)."""
    if len(node.args) >= 3:
        exception_type = node.args[0].value
        code_to_test = node.args[2].value
        new_attr = cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="raises"))
        new_args = [
            cst.Arg(value=exception_type),
            cst.Arg(value=cst.Call(func=cst.Name(value="lambda"), args=[cst.Arg(value=code_to_test)])),
        ]
        return cst.Call(func=new_attr, args=new_args)
    return node


def transform_assert_isinstance(node: cst.Call) -> cst.CSTNode:
    """Transform assertIsInstance to isinstance assert."""
    if len(node.args) >= 2:
        call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=call)
    return node


def transform_assert_not_isinstance(node: cst.Call) -> cst.CSTNode:
    """Transform assertNotIsInstance to not isinstance assert."""
    if len(node.args) >= 2:
        call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=call))
    return node


def transform_assertions_string_based(code: str, test_prefixes: list[str] | None = None) -> str:
    """Transform unittest assertion methods using string replacement.

    This was previously the `_transform_assertions_string_based` method on the
    `UnittestToPytestTransformer` class. It is extracted for reuse and to
    decouple string-based fallbacks from the transformer instance.
    """

    # Use balanced/safe replacements to avoid corrupting nested expressions
    def _fmt_eq(a: str, b: str) -> str:
        return f"assert {a} == {b}"

    code = safe_replace_two_arg_call(code, "assertEqual", _fmt_eq)
    code = safe_replace_two_arg_call(code, "assertEquals", _fmt_eq)
    code = safe_replace_two_arg_call(code, "assertNotEqual", lambda a, b: f"assert {a} != {b}")
    code = safe_replace_two_arg_call(code, "assertNotEquals", lambda a, b: f"assert {a} != {b}")
    code = safe_replace_one_arg_call(code, "assertTrue", lambda a: f"assert {a}")
    code = safe_replace_one_arg_call(code, "assertIsTrue", lambda a: f"assert {a}")
    code = safe_replace_one_arg_call(code, "assertFalse", lambda a: f"assert not {a}")
    code = safe_replace_one_arg_call(code, "assertIsFalse", lambda a: f"assert not {a}")
    code = safe_replace_two_arg_call(code, "assertIs", lambda a, b: f"assert {a} is {b}")
    code = safe_replace_two_arg_call(code, "assertIsNot", lambda a, b: f"assert {a} is not {b}")
    code = safe_replace_one_arg_call(code, "assertIsNone", lambda a: f"assert {a} is None")
    code = safe_replace_one_arg_call(code, "assertIsNotNone", lambda a: f"assert {a} is not None")
    code = safe_replace_two_arg_call(code, "assertIn", lambda a, b: f"assert {a} in {b}")
    code = safe_replace_two_arg_call(code, "assertNotIn", lambda a, b: f"assert {a} not in {b}")
    code = safe_replace_two_arg_call(code, "assertIsInstance", lambda a, b: f"assert isinstance({a}, {b})")
    code = safe_replace_two_arg_call(code, "assertNotIsInstance", lambda a, b: f"assert not isinstance({a}, {b})")
    for fn in [
        "assertDictEqual",
        "assertDictEquals",
        "assertListEqual",
        "assertListEquals",
        "assertSetEqual",
        "assertSetEquals",
        "assertTupleEqual",
        "assertTupleEquals",
        "assertSequenceEqual",
        "assertMultiLineEqual",
    ]:
        code = safe_replace_two_arg_call(code, fn, _fmt_eq)

    # Safe replacement for assertCountEqual(a, b) -> assert sorted(a) == sorted(b)
    def _fmt_count_equal(a: str, b: str) -> str:
        return f"assert sorted({a}) == sorted({b})"

    code = safe_replace_two_arg_call(code, "assertCountEqual", _fmt_count_equal)

    # Normalize test method names according to prefixes (basic heuristic)
    def _normalize_name(m: re.Match[str]) -> str:
        name = m.group(1)
        rest = m.group(2)
        if rest and not rest.startswith("_"):
            normalized = f"{name}_{rest}"
        else:
            normalized = f"{name}{rest}"
        normalized = re.sub(r"__+", "_", normalized)
        normalized = re.sub(r"[^0-9a-zA-Z_]", "_", normalized)
        return f"def {normalized}(self)"

    prefixes = "|".join(map(re.escape, test_prefixes or ["test"]))
    code = re.sub(rf"def\s+({prefixes})([^\s(]*)\(self\)", _normalize_name, code)

    # Transform exception assertions (basic transformation for now)
    code = re.sub(r"self\.assertRaises\s*\(\s*([^,]+)\s*\)", r"pytest.raises(\1)", code)
    code = re.sub(r"self\.assertRaisesRegex\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)", r"pytest.raises(\1)", code)
    code = re.sub(r"self\.assertRaisesRegexp\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)", r"pytest.raises(\1)", code)

    # Transform unittest.main() calls
    code = re.sub(r"unittest\.main\s*\(\s*\)", r"pytest.main()", code)

    return code
