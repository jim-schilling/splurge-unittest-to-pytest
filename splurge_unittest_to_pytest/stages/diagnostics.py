from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Any



def diagnostics_enabled() -> bool:
    val = os.environ.get("SPLURGE_ENABLE_DIAGNOSTICS", "0")
    return val in ("1", "true", "True", "yes", "on")


def create_diagnostics_dir() -> Optional[Path]:
    """Create a per-run diagnostics directory and write a marker file.

    Returns the created Path or None on failure or when diagnostics are disabled.
    """
    if not diagnostics_enabled():
        return None
    try:
        tmpdir = tempfile.mkdtemp(prefix="splurge-diagnostics-")
        out_dir = Path(tmpdir)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        marker = out_dir / f"splurge-diagnostics-{ts}"
        try:
            marker.write_text(str(out_dir.resolve()), encoding="utf-8")
        except Exception:
            return None
        return out_dir
    except Exception:
        return None


def write_snapshot(out_dir: Optional[Path], filename: str, module: Any) -> None:
    """Write a snapshot of `module` to `out_dir/filename`.

    The function is defensive: it no-ops when out_dir is None or the module
    doesn't expose source code.
    """
    try:
        if out_dir is None:
            return
        if not isinstance(out_dir, Path):
            return
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        src = getattr(module, "code", None)
        if src is None:
            try:
                src = module.code
            except Exception:
                src = None
        if src is not None:
            out_path.write_text(src, encoding="utf-8")
    except Exception:
        # Swallow any errors — diagnostics must not break pipeline
        return
