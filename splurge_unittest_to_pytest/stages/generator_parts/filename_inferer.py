"""Infer filename literals from recorded local assignments.

Try to recover a filename string when a recorded local assignment is a
:class:`libcst.Call` whose first positional argument is a string
literal. Return the unquoted filename on success or ``None`` when no
filename can be inferred.

Publics:
    infer_filename_for_local
"""

from __future__ import annotations

from typing import Any, Optional

import libcst as cst

DOMAINS = ["generator", "naming"]

# Associated domains for this module


def infer_filename_for_local(local_name: str, cls_obj: Any) -> Optional[str]:
    """Return a filename string inferred from a recorded local assignment.

    If the recorded assignment is a libcst.Call with a string literal as
    its first positional argument, return the unquoted string value.
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
