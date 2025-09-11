"""Helpers for class base checks used by the transformer."""

from __future__ import annotations


import libcst as cst


def is_unittest_testcase_base(base: cst.Arg) -> bool:
    """Return True if the class base represents unittest.TestCase or TestCase.

    Accepts patterns like `unittest.TestCase` or just `TestCase`.
    """
    if isinstance(base.value, cst.Attribute):
        if (
            isinstance(base.value.value, cst.Name)
            and base.value.value.value == "unittest"
            and base.value.attr.value == "TestCase"
        ):
            return True
    elif isinstance(base.value, cst.Name):
        if base.value.value == "TestCase":
            return True
    return False
