"""Assertion conversion dispatch helpers."""
from typing import Sequence

import libcst as cst

from .assertions import (
    _assert_equal,
    _assert_not_equal,
    _assert_true,
    _assert_false,
    _assert_is_none,
    _assert_is_not_none,
    _assert_in,
    _assert_not_in,
    _assert_is_instance,
    _assert_not_is_instance,
    _assert_greater,
    _assert_greater_equal,
    _assert_less,
    _assert_less_equal,
)


def convert_assertion(method_name: str, args: Sequence[cst.Arg]) -> cst.BaseSmallStatement | None:
    """Convert unittest assertion name+args to a pytest assertion node or None."""
    try:
        if method_name in ("assertRaises", "assertRaisesRegex"):
            return None

        assertions_map = {
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

        converter = assertions_map.get(method_name)
        if converter:
            return converter(args)
    except (AttributeError, TypeError, ValueError):
        return None

    return None
