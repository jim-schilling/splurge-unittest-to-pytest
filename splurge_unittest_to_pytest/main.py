"""Programmatic API for splurge_unittest_to_pytest.

This module exposes a small programmatic entry point, ``migrate``, which
is used by the CLI and tests. It delegates work to
``MigrationOrchestrator`` and returns a ``Result`` containing the list
of written target paths.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from __future__ import annotations

from collections.abc import Iterable

from .context import MigrationConfig
from .migration_orchestrator import MigrationOrchestrator
from .result import Result


def migrate(source_files: Iterable[str] | str, config: MigrationConfig | None = None) -> Result[list[str]]:
    """Migrate one or more source files programmatically.

    Args:
        source_files: Iterable of file paths (or single path string).
        config: Optional ``MigrationConfig`` to control migration behavior.

    Returns:
        ``Result`` containing a list of written target file paths on
        success. On failure a failure ``Result`` is returned.
    """
    if isinstance(source_files, str):
        files = [source_files]
    else:
        files = list(source_files)

    if config is None:
        config = MigrationConfig()

    orchestrator = MigrationOrchestrator()
    written: list[str] = []
    # Collect per-file generated code when running in dry-run so callers
    # (CLI) can display the converted code without writing files.
    generated_map: dict[str, str] = {}

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
            # Collect generated_code if present in the per-file result metadata
            try:
                meta = getattr(res, "metadata", None) or {}
                if isinstance(meta, dict) and "generated_code" in meta:
                    # If multiple targets were returned for this source, map
                    # each target to the same generated code; otherwise map
                    # the single target path.
                    gen = meta["generated_code"]
                    if isinstance(data, list):
                        for d in data:
                            generated_map[str(d)] = gen
                    elif data is not None:
                        generated_map[str(data)] = gen
                    else:
                        generated_map[str(src)] = gen
            except Exception:
                pass
        else:
            err = getattr(res, "error", Exception("Migration failed"))
            return Result.failure(err)

    # Attach generated_code map to metadata if present
    metadata = {"generated_code": generated_map} if generated_map else None
    return Result.success(written, metadata=metadata)
