"""Optional diagnostics and run-time instrumentation helpers.

Utilities used by the pipeline to create per-run diagnostics folders,
write snapshot files, and centralize diagnostics-related checks. These
helpers are defensive and no-op when diagnostics are disabled so normal
runs are unaffected.

Publics:
    diagnostics_enabled, diagnostics_verbose, create_diagnostics_dir,
    write_snapshot

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DOMAINS = ["stages", "diagnostics"]


def diagnostics_enabled() -> bool:
    """Return True when diagnostics are enabled via environment var.

    Treats common truthy values ("1", "true", "yes", "on") as enabled.
    """

    val = os.environ.get("SPLURGE_ENABLE_DIAGNOSTICS", "0")
    return val in ("1", "true", "True", "yes", "on")


def diagnostics_verbose() -> bool:
    """Return True when verbose diagnostics logging is enabled."""

    val = os.environ.get("SPLURGE_DIAGNOSTICS_VERBOSE", "0")
    return val in ("1", "true", "True", "yes", "on")


_logger = logging.getLogger("splurge.diagnostics")


def create_diagnostics_dir() -> Optional[Path]:
    """Create a per-run diagnostics directory and write a marker file.

    When diagnostics are enabled this function creates a temporary directory
    (optionally under ``SPLURGE_DIAGNOSTICS_ROOT``) and writes a small marker
    file containing the directory path. Returns the created :class:`Path` or
    ``None`` when diagnostics are disabled or creation fails.
    """

    if not diagnostics_enabled():
        return None
    try:
        # Allow an override to put diagnostics under a custom root. This is
        # useful for CI systems or when a repository-local location is
        # preferred. If the override is not set, fall back to the system temp
        # directory (tempfile.gettempdir()).
        override = os.environ.get("SPLURGE_DIAGNOSTICS_ROOT")
        if override:
            root_tmp = override
        else:
            root_tmp = tempfile.gettempdir()
        tmpdir = tempfile.mkdtemp(prefix="splurge-diagnostics-", dir=root_tmp)
        out_dir = Path(tmpdir)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        marker = out_dir / f"splurge-diagnostics-{ts}"
        try:
            marker.write_text(str(out_dir.resolve()), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive logging path
            if diagnostics_enabled():
                try:
                    if diagnostics_verbose():
                        _logger.exception("failed to write diagnostics marker")
                    else:
                        _logger.error("failed to write diagnostics marker: %s", exc)
                except Exception:
                    pass
            return None
        return out_dir
    except Exception:
        if diagnostics_enabled():
            try:
                if diagnostics_verbose():
                    _logger.exception("failed to create diagnostics dir")
                else:
                    _logger.error("failed to create diagnostics dir")
            except Exception:
                pass
        return None


def write_snapshot(
    out_dir: Optional[Path],
    filename: str,
    module: Any,
) -> None:
    """Write a snapshot of ``module`` to ``out_dir/filename``.

    The function is defensive: it no-ops when ``out_dir`` is ``None`` or the
    module does not expose source code. Any write failures are swallowed but
    logged when diagnostics are enabled so instrumentation does not break
    normal runs.
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
    except Exception as exc:  # pragma: no cover - defensive logging path
        # Swallow errors but emit a helpful log message when diagnostics are
        # enabled so operators can discover problems without failing runs.
        if diagnostics_enabled():
            try:
                if diagnostics_verbose():
                    _logger.exception("write_snapshot failed")
                else:
                    _logger.error("write_snapshot failed: %s", exc)
            except Exception:
                pass
        return
