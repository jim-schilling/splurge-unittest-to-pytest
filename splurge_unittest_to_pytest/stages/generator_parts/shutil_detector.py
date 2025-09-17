"""Detect whether generated cleanup code requires the ``shutil`` API.

The routine renders small statement nodes to source and looks for
``shutil`` usage. It is deliberately conservative and returns False on
rendering errors.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Sequence, Any

import libcst as cst

DOMAINS = ["generator", "helpers"]


# Associated domains for this module


def cleanup_needs_shutil(stmts: Sequence[Any]) -> bool:
    """Detect whether any provided statements reference the ``shutil`` API.

    The implementation renders statements to source and looks for the
    substrings ``shutil.`` or ``import shutil``. Rendering errors are
    ignored and the function returns False in those cases.
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
