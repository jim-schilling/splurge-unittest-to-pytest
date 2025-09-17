"""Utilities for analyzing :class:`libcst.Call` nodes.

Small helper used to detect call patterns such as ``self.method(...)``
so stages can special-case instance method invocations during
conversion. The primary exported function is :func:`is_self_call`.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from typing import Sequence

import libcst as cst

DOMAINS = ["converter", "helpers"]

# Associated domains for this module
# Moved to top of module after imports.


def is_self_call(call_node: cst.Call) -> tuple[str, Sequence[cst.Arg]] | None:
    """Return (method_name, args) if call_node is self.method(...), else None."""
    try:
        if isinstance(call_node.func, cst.Attribute):
            if isinstance(call_node.func.value, cst.Name):
                if call_node.func.value.value == "self":
                    method_name = call_node.func.attr.value
                    return method_name, call_node.args
    except Exception:
        pass
    return None
