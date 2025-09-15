"""Command-line wrapper to locate and print splurge diagnostics artifacts.

This module provides a `main()` function so it can be executed as a module:

    python -m splurge_unittest_to_pytest.print_diagnostics --root /path/to/root

It mirrors the earlier `tools/print_diagnostics.py` helper for backwards
compatibility.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from typing import Optional
from pathlib import Path

DOMAINS = ["diagnostics"]

# Associated domains for this module
# Placed after imports for discoverability.


def find_diagnostics_root(cli_root: Optional[str]) -> Path:
    if cli_root:
        return Path(cli_root)
    env = os.environ.get("SPLURGE_DIAGNOSTICS_ROOT")
    if env:
        return Path(env)
    return Path(tempfile.gettempdir())


def find_most_recent_run(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    for p in root.iterdir():
        if p.is_dir() and p.name.startswith("splurge-diagnostics-"):
            try:
                candidates.append((p.stat().st_mtime, p))
            except Exception:
                continue
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def print_run_info(run_dir: Path) -> None:
    marker_files = list(run_dir.glob("splurge-diagnostics-*"))
    print(f"Diagnostics run directory: {run_dir}")
    if marker_files:
        for m in marker_files:
            try:
                print("--- marker:", m.name)
                print(m.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Failed to read marker {m}: {e}", file=sys.stderr)
    else:
        print("No marker file found in run dir")

    print("\nFiles in diagnostics run:")
    for p in sorted(run_dir.iterdir()):
        print("  ", p.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="splurge-print-diagnostics")
    parser.add_argument("--root", help="Diagnostics root directory to search")
    args = parser.parse_args(argv)

    root = find_diagnostics_root(args.root)
    print(f"Searching diagnostics root: {root}")
    run = find_most_recent_run(root)
    if run is None:
        print("No diagnostics runs found under root.")
        return 0
    print_run_info(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
