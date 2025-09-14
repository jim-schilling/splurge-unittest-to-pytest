"""Assertion conversion helpers extracted from the monolithic converter.

These helpers are pure functions (avoid touching transformer instance state)
so they can be moved and tested independently. Instance methods in the
transformer will delegate to these functions.
"""

from __future__ import annotations

from typing import Sequence, Callable

import libcst as cst


def _assert_equal(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertEqual to assert ==."""
    try:
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=args[1].value)],
                )
            )
    except (AttributeError, TypeError, ValueError):
        pass
    return cst.Assert(test=cst.Name("False"))


def _assert_not_equal(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertNotEqual to assert !=."""
    try:
        if len(args) >= 2:
            return cst.Assert(
                test=cst.Comparison(
                    left=args[0].value,
                    comparisons=[cst.ComparisonTarget(operator=cst.NotEqual(), comparator=args[1].value)],
                )
            )
    except (AttributeError, TypeError, ValueError):
        pass
    return cst.Assert(test=cst.Name("False"))


def _assert_true(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertTrue to assert."""
    try:
        if len(args) >= 1:
            return cst.Assert(test=args[0].value)
    except (AttributeError, TypeError, ValueError):
        pass
    return cst.Assert(test=cst.Name("False"))


def _assert_false(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertFalse to assert not."""
    try:
        if len(args) >= 1:
            return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=args[0].value))
    except (AttributeError, TypeError, ValueError):
        pass
    return cst.Assert(test=cst.Name("False"))


def _assert_is_none(args: Sequence[cst.Arg]) -> cst.Assert | None:
    """Convert assertIsNone to assert ... is None.

    Returns None for literal arguments to avoid producing questionable code
    such as `assert 1 is None`.
    """
    if len(args) >= 1:
        left_expr = args[0].value
        if isinstance(left_expr, (cst.Integer, cst.Float, cst.SimpleString)):
            return None

        return cst.Assert(
            test=cst.Comparison(
                left=left_expr,
                comparisons=[cst.ComparisonTarget(operator=cst.Is(), comparator=cst.Name("None"))],
            )
        )
    return cst.Assert(test=cst.Name("False"))


def _assert_is_not_none(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertIsNotNone to assert ... is not None."""
    if len(args) >= 1:
        left_expr = args[0].value
        return cst.Assert(
            test=cst.Comparison(
                left=left_expr,
                comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))],
            )
        )
    return cst.Assert(test=cst.Name("False"))


def _assert_in(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertIn to assert ... in ..."""
    if len(args) >= 2:
        return cst.Assert(
            test=cst.Comparison(
                left=args[0].value,
                comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=args[1].value)],
            )
        )
    return cst.Assert(test=cst.Name("False"))


def _assert_not_in(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertNotIn to assert ... not in ..."""
    if len(args) >= 2:
        return cst.Assert(
            test=cst.Comparison(
                left=args[0].value,
                comparisons=[cst.ComparisonTarget(operator=cst.NotIn(), comparator=args[1].value)],
            )
        )
    return cst.Assert(test=cst.Name("False"))


def _assert_is_instance(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertIsInstance to assert isinstance(...)."""
    if len(args) >= 2:
        isinstance_call = cst.Call(func=cst.Name("isinstance"), args=[args[0], args[1]])
        return cst.Assert(test=isinstance_call)
    return cst.Assert(test=cst.Name("False"))


def _assert_not_is_instance(args: Sequence[cst.Arg]) -> cst.Assert:
    """Convert assertNotIsInstance to assert not isinstance(...)."""
    if len(args) >= 2:
        isinstance_call = cst.Call(func=cst.Name("isinstance"), args=[args[0], args[1]])
        return cst.Assert(test=cst.UnaryOperation(operator=cst.Not(), expression=isinstance_call))
    return cst.Assert(test=cst.Name("False"))


def _assert_greater(args: Sequence[cst.Arg]) -> cst.Assert:
    if len(args) >= 2:
        return cst.Assert(
            test=cst.Comparison(
                left=args[0].value,
                comparisons=[cst.ComparisonTarget(operator=cst.GreaterThan(), comparator=args[1].value)],
            )
        )
    return cst.Assert(test=cst.Name("False"))


def _assert_greater_equal(args: Sequence[cst.Arg]) -> cst.Assert:
    if len(args) >= 2:
        return cst.Assert(
            test=cst.Comparison(
                left=args[0].value,
                comparisons=[cst.ComparisonTarget(operator=cst.GreaterThanEqual(), comparator=args[1].value)],
            )
        )
    return cst.Assert(test=cst.Name("False"))


def _assert_less(args: Sequence[cst.Arg]) -> cst.Assert:
    if len(args) >= 2:
        return cst.Assert(
            test=cst.Comparison(
                left=args[0].value,
                comparisons=[cst.ComparisonTarget(operator=cst.LessThan(), comparator=args[1].value)],
            )
        )
    return cst.Assert(test=cst.Name("False"))


def _assert_less_equal(args: Sequence[cst.Arg]) -> cst.Assert:
    if len(args) >= 2:
        return cst.Assert(
            test=cst.Comparison(
                left=args[0].value,
                comparisons=[cst.ComparisonTarget(operator=cst.LessThanEqual(), comparator=args[1].value)],
            )
        )
    return cst.Assert(test=cst.Name("False"))


__all__: list[str] = [
    "_assert_equal",
    "_assert_not_equal",
    "_assert_true",
    "_assert_false",
    "_assert_is_none",
    "_assert_is_not_none",
    "_assert_in",
    "_assert_not_in",
    "_assert_is_instance",
    "_assert_not_is_instance",
    "_assert_greater",
    "_assert_greater_equal",
    "_assert_less",
    "_assert_less_equal",
]

# Public mapping of unittest assertion method names to converter functions.
# This lets callers use a single source-of-truth for dispatching conversions.
ASSERTIONS_MAP: dict[str, Callable[[Sequence[cst.Arg]], cst.Assert | None]] = {
    "assertEqual": _assert_equal,
    "assertNotEqual": _assert_not_equal,
    "assertTrue": _assert_true,
    "assertFalse": _assert_false,
    "assertIsNone": _assert_is_none,
    "assertIsNotNone": _assert_is_not_none,
    "assertIn": _assert_in,
    "assertNotIn": _assert_not_in,
    "assertIsInstance": _assert_is_instance,
    "assertNotIsInstance": _assert_not_is_instance,
    "assertGreater": _assert_greater,
    "assertGreaterEqual": _assert_greater_equal,
    "assertLess": _assert_less,
    "assertLessEqual": _assert_less_equal,
}

# Export the map as part of the module's public API
__all__.append("ASSERTIONS_MAP")
