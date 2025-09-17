"""Dispatch helper that maps unittest assertion names to converters.

Expose ``convert_assertion`` which takes a unittest-style assertion
method name and its argument list and returns a ``libcst`` node
representing the corresponding pytest-style assertion. The dispatcher
delegates to the concrete converters defined in :mod:`.assertions`.

Publics:
    convert_assertion: Convert a unittest assertion method into a libcst node.

Copyright (c) 2025 Jim Schilling

License: MIT
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
