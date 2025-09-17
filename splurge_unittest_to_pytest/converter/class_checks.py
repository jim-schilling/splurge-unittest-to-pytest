"""Utilities for inspecting class base expressions.

Small helpers to detect whether a class inherits from ``unittest.TestCase``
or a bare ``TestCase`` identifier. These utilities are used early in the
pipeline to remove unittest-specific bases when converting to pytest.

Publics:
    is_unittest_testcase_base: Detect ``unittest.TestCase`` or ``TestCase`` bases.
    remove_unittest_bases: Return bases with unittest TestCase entries removed.
"""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter"]

# Associated domains for this module
# Moved to top of module after imports.


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


def remove_unittest_bases(bases: list[cst.Arg]) -> list[cst.Arg]:
    """Return a new list of bases with unittest.TestCase/TestCase removed."""
    return [b for b in bases if not is_unittest_testcase_base(b)]
