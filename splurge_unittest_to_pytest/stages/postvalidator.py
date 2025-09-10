"""PostValidator stage: sanity-check the generated module by attempting to
serialize and parse it back, returning errors if any.
"""
from __future__ import annotations

from typing import Any, Dict

import libcst as cst


def postvalidator_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    module: cst.Module = context.get("module")
    if module is None:
        return {"module": module}
    # Try to generate code and reparse
    code = module.code
    try:
        _ = cst.parse_module(code)
    except Exception as exc:  # parse error
        # attach an error key to context for later inspection
        return {"module": module, "postvalidator_error": str(exc)}
    return {"module": module}
