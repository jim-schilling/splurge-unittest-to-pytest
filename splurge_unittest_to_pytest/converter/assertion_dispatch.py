"""Dispatch helper for converting unittest assertions to pytest.

This module exposes ``convert_assertion`` which maps a unittest-style
assertion method name and its arguments to a corresponding
:mod:`libcst` node representing a pytest-style assertion. The dispatcher
delegates to the implementations found in :mod:`.assertions`.
"""

from typing import Sequence

import libcst as cst

from .assertions import ASSERTIONS_MAP

DOMAINS = ["converter", "assertions"]

# Associated domains for this module
# Moved to top of module after imports.


def convert_assertion(method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:
    """Convert unittest assertion name+args to a pytest assertion node or None."""
    try:
        if method_name in ("assertRaises", "assertRaisesRegex"):
            return None

        converter = ASSERTIONS_MAP.get(method_name)
        if converter:
            return converter(args)
    except (AttributeError, TypeError, ValueError):
        return None

    return None
