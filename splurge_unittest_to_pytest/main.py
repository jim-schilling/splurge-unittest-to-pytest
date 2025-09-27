"""Programmatic API for splurge_unittest_to_pytest.

Exports a single function `migrate(source_files, config=None)` which the CLI
and tests import. This module keeps the logic small: it instantiates the
MigrationOrchestrator and delegates per-file migration, collecting the
written output paths and returning them in a Result.
"""

from __future__ import annotations

from collections.abc import Iterable

from .context import MigrationConfig
from .migration_orchestrator import MigrationOrchestrator
from .result import Result


def migrate(source_files: Iterable[str] | str, config: MigrationConfig | None = None) -> Result[list[str]]:
    """Migrate one or more source files programmatically.

    Args:
        source_files: Iterable of file paths (or single path string)
        config: Optional MigrationConfig

    Returns:
        Result containing a list of written target file paths on success.
    """
    if isinstance(source_files, str):
        files = [source_files]
    else:
        files = list(source_files)

    if config is None:
        config = MigrationConfig()

    orchestrator = MigrationOrchestrator()
    written: list[str] = []

    for src in files:
        res = orchestrator.migrate_file(src, config)

        # Defensive handling: tests may monkeypatch migrate_file to return a
        # lightweight DummyResult without `.data`. Handle objects that expose
        # `is_success()` and optionally `data` or `error`.
        try:
            ok = bool(res.is_success())
        except Exception:
            ok = bool(getattr(res, "_success", False))

        if ok:
            data = getattr(res, "data", None)
            if data is None:
                # If no data was returned, fall back to the source path.
                written.append(src)
            elif isinstance(data, list):
                written.extend(data)
            else:
                written.append(str(data))
        else:
            err = getattr(res, "error", Exception("Migration failed"))
            return Result.failure(err)

    return Result.success(written)
