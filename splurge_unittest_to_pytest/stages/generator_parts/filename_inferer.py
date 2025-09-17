"""Infer filename string literals from recorded local assignments.

Extracted from ``stages/generator.py`` to simplify testing and separate
concerns. The primary function returns a filename string when a recorded
local assignment corresponds to a Call whose first positional argument is
a string literal.
"""

from __future__ import annotations

from typing import Any, Optional

import libcst as cst

DOMAINS = ["generator", "naming"]

# Associated domains for this module


def infer_filename_for_local(local_name: str, cls_obj: Any) -> Optional[str]:
    """Return a filename string inferred from a recorded local assignment.

    The collector records local assignments as a mapping from local name to
    a tuple (call_node, ...). We only handle the simple case where the
    assignment is a Call whose first positional argument is a string literal.
    """
    try:
        local_map = getattr(cls_obj, "local_assignments", {}) or {}
        if local_name not in local_map:
            return None
        val = local_map[local_name]
        # local_map entries may be (call, idx) or (call, idx, refs)
        if isinstance(val, tuple) or isinstance(val, list):
            assigned_call = val[0]
        else:
            assigned_call = val
        if not isinstance(assigned_call, cst.Call):
            return None
        if assigned_call.args:
            for a in assigned_call.args:
                if isinstance(getattr(a, "value", None), cst.SimpleString):
                    s = getattr(a.value, "value", "")
                    if len(s) >= 2 and (s[0] == s[-1] == '"' or s[0] == s[-1] == "'"):
                        return s[1:-1]
        return None
    except Exception:
        return None
