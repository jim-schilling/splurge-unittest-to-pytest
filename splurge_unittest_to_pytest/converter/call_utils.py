"""Utilities for analyzing Call nodes."""

from typing import Sequence, Tuple

import libcst as cst


def is_self_call(call_node: cst.Call) -> Tuple[str, Sequence[cst.Arg]] | None:
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
