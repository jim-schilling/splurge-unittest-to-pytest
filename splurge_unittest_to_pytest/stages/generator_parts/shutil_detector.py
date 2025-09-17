from __future__ import annotations

from typing import Sequence, Any

import libcst as cst

DOMAINS = ["generator", "helpers"]


# Associated domains for this module


def cleanup_needs_shutil(stmts: Sequence[Any]) -> bool:
    """Return True if any statement appears to reference shutil.

    Renders statements to source and searches for ``shutil.`` or
    ``import shutil``; rendering errors are ignored.
    """
    for s in stmts:
        try:
            rendered = cst.Module(body=[s]).code
            if "shutil." in rendered or "import shutil" in rendered:
                return True
        except Exception:
            # ignore rendering errors; keep conservative behavior
            pass
    return False
