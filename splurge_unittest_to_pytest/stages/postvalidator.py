"""Post-validation stage that sanity-checks generated modules.

Attempts to parse the generated module source to detect serialization or
syntax errors introduced during conversion. If parsing fails the stage
attaches a ``postvalidator_error`` entry to the pipeline context.
"""

from __future__ import annotations

from typing import Any

import libcst as cst

DOMAINS = ["stages", "validation"]

# Associated domains for this module


def postvalidator_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_module: Any = context.get("module")
    if maybe_module is None:
        return {}

    # Accept either a real libcst.Module or any module-like object that
    # exposes a .code attribute (tests provide a simple object with .code).
    code = getattr(maybe_module, "code", None)
    if not isinstance(code, str):
        # Nothing to validate; return the module-like object unchanged.
        return {"module": maybe_module}

    # Try to generate code and reparse
    try:
        _ = cst.parse_module(code)
    except Exception as exc:  # parse error
        # attach an error key to context for later inspection
        return {"module": maybe_module, "postvalidator_error": str(exc)}
    return {"module": maybe_module}
