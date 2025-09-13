"""Assertion conversion dispatch helpers."""

from typing import Sequence

import libcst as cst

from .assertions import ASSERTIONS_MAP


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
