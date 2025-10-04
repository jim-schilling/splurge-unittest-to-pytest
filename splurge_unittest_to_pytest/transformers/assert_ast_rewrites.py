"""AST-shaped assertion rewrite helpers.

This module contains the pure, structural transformations for
unittest-style assertions that do not depend on caplog or context
manager rewrites. These helpers operate on libcst nodes and are
safe to test in isolation.
"""

from dataclasses import dataclass
from typing import Any

import libcst as cst

__all__ = [
    "ParenthesizedExpression",
    "parenthesized_expression",
    "transform_assert_equal",
    "transform_assert_not_almost_equal",
    "transform_assert_true",
    "transform_assert_false",
    "transform_assert_is",
    "transform_assert_not_equal",
    "transform_assert_is_not",
    "transform_assert_is_none",
    "transform_assert_is_not_none",
    "transform_assert_not_in",
    "transform_assert_isinstance",
    "transform_assert_not_isinstance",
    "transform_assert_count_equal",
    "transform_assert_multiline_equal",
    "transform_assert_regex",
    "transform_assert_not_regex",
    "transform_assert_in",
    "transform_assert_dict_equal",
    "transform_assert_list_equal",
    "transform_assert_set_equal",
    "transform_assert_tuple_equal",
    "transform_assert_greater",
    "transform_assert_greater_equal",
    "transform_assert_less",
    "transform_assert_less_equal",
    "transform_assert_almost_equal",
    "transform_assert_almost_equals",
    "transform_assert_not_almost_equals",
]


@dataclass(frozen=True)
class ParenthesizedExpression:
    """Capture parentheses metadata attached to an expression node."""

    has_parentheses: bool
    lpar: tuple[cst.LeftParen, ...]
    rpar: tuple[cst.RightParen, ...]

    def strip(self, expr: cst.BaseExpression) -> cst.BaseExpression:
        if not self.has_parentheses or not hasattr(expr, "with_changes"):
            return expr

        updates: dict[str, tuple[object, ...]] = {}
        if hasattr(expr, "lpar"):
            updates["lpar"] = ()
        if hasattr(expr, "rpar"):
            updates["rpar"] = ()

        return expr.with_changes(**updates) if updates else expr

    def restore(self, expr: cst.BaseExpression) -> cst.BaseExpression:
        if not self.has_parentheses or not hasattr(expr, "with_changes"):
            return expr

        updates: dict[str, tuple[object, ...]] = {}
        if hasattr(expr, "lpar"):
            updates["lpar"] = self.lpar
        if hasattr(expr, "rpar"):
            updates["rpar"] = self.rpar

        return expr.with_changes(**updates) if updates else expr


def parenthesized_expression(expr: cst.BaseExpression) -> ParenthesizedExpression:
    lpar = tuple(getattr(expr, "lpar", ()))
    rpar = tuple(getattr(expr, "rpar", ()))
    return ParenthesizedExpression(has_parentheses=bool(lpar or rpar), lpar=lpar, rpar=rpar)


def transform_assert_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_almost_equal(node: cst.Call, config: Any | None = None) -> cst.CSTNode:
    if len(node.args) >= 2:
        left = node.args[0].value
        right = node.args[1].value
        places = None
        for arg in node.args:
            if arg.keyword and isinstance(arg.keyword, cst.Name) and arg.keyword.value == "places":
                places = arg.value
                break
        if places is None:
            places_value = getattr(config, "assert_almost_equal_places", 7) if config else 7
            places = cst.Integer(value=str(places_value))
        diff = cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right)
        round_call = cst.Call(func=cst.Name(value="round"), args=[cst.Arg(value=diff), cst.Arg(value=places)])
        comp = cst.Comparison(
            left=round_call,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="0"))],
        )
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=comp))
    return node


def transform_assert_true(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 1:
        return cst.Assert(test=node.args[0].value)
    return node


def transform_assert_false(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 1:
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=node.args[0].value))
    return node


def transform_assert_is(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_none(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_is_not_none(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 1:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name(value="None"))],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_not_in(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.NotIn(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_isinstance(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        isinstance_call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=isinstance_call)
    return node


def transform_assert_not_isinstance(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        isinstance_call = cst.Call(
            func=cst.Name(value="isinstance"),
            args=[cst.Arg(value=node.args[0].value), cst.Arg(value=node.args[1].value)],
        )
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=isinstance_call))
    return node


def transform_assert_count_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        left = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[0].value)])
        right = cst.Call(func=cst.Name(value="sorted"), args=[cst.Arg(value=node.args[1].value)])
        comp = cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=right)])
        return cst.Assert(test=comp)
    return node


def transform_assert_multiline_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_regex(
    node: cst.Call, re_alias: str | None = None, re_search_name: str | None = None
) -> cst.CSTNode:
    if len(node.args) >= 2:
        if re_search_name:
            func: cst.BaseExpression = cst.Name(value=re_search_name)
        else:
            re_name = re_alias or "re"
            func = cst.Attribute(value=cst.Name(value=re_name), attr=cst.Name(value="search"))

        call = cst.Call(func=func, args=[cst.Arg(value=node.args[1].value), cst.Arg(value=node.args[0].value)])
        return cst.Assert(test=call)
    return node


def transform_assert_not_regex(
    node: cst.Call, re_alias: str | None = None, re_search_name: str | None = None
) -> cst.CSTNode:
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
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_dict_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_list_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_set_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_tuple_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_greater(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_greater_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.GreaterThanEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_less(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.LessThan(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_less_equal(node: cst.Call) -> cst.CSTNode:
    if len(node.args) >= 2:
        comp = cst.Comparison(
            left=node.args[0].value,
            comparisons=[cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=node.args[1].value)],
        )
        return cst.Assert(test=comp)
    return node


def transform_assert_almost_equal(node: cst.Call, config: Any | None = None) -> cst.CSTNode:
    if len(node.args) >= 2:
        left = node.args[0].value
        right = node.args[1].value
        places = None
        for arg in node.args:
            if arg.keyword and isinstance(arg.keyword, cst.Name) and arg.keyword.value == "places":
                places = arg.value
                break
        if places is None:
            approx_call = cst.Call(
                func=cst.Attribute(value=cst.Name(value="pytest"), attr=cst.Name(value="approx")),
                args=[cst.Arg(value=right)],
            )
            comp = cst.Comparison(
                left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=approx_call)]
            )
            return cst.Assert(test=comp)
        else:
            diff = cst.BinaryOperation(left=left, operator=cst.Subtract(), right=right)
            round_call = cst.Call(func=cst.Name(value="round"), args=[cst.Arg(value=diff), cst.Arg(value=places)])
            comp = cst.Comparison(
                left=round_call,
                comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer(value="0"))],
            )
            return cst.Assert(test=comp)
    return node


def transform_assert_almost_equals(node: cst.Call) -> cst.CSTNode:
    return transform_assert_almost_equal(node)


def transform_assert_not_almost_equals(node: cst.Call) -> cst.CSTNode:
    # delegate to not_almost logic if present
    return transform_assert_not_almost_equal(node)
