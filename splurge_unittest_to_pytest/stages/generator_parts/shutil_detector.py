from __future__ import annotations

from typing import Sequence, Any

import libcst as cst

DOMAINS = ["generator", "helpers"]


# Associated domains for this module


def cleanup_needs_shutil(stmts: Sequence[Any]) -> bool:
    """Return True if any statement in stmts appears to reference shutil.

    This mirrors the tolerant, text-based detection used in the legacy
    generator: it renders statements to source and looks for
    either "shutil." or "import shutil". Rendering may fail for odd
    shapes; in that case the statement is ignored (conservative behavior).
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
