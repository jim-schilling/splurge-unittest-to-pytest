#!/usr/bin/env python3
"""Safe test rename utility.

Usage:
  - Dry-run (default): prints proposed renames
  - --apply: actually performs renames
  - --update-imports: attempt to update import references in test and package files
  - --map-file <path>: optional CSV mapping file (current,new) to drive renames

The script is conservative: by default it only prints planned actions. If --apply
is passed it will perform os.rename; if --update-imports is passed it will do a
simple regex replace of import statements that reference old module names.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DEFAULT_MAP = {
    # Example: if you want to include default normalization entries, add here.
}


def load_map_from_csv(path: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip().startswith("#"):
                continue
            if len(row) < 2:
                continue
            src, dst = row[0].strip(), row[1].strip()
            mapping[src] = dst
    return mapping


def discover_tests(root: Path, exts: List[str], max_depth: int) -> List[Path]:
    """Recursively discover files under `root` matching one of `exts` and within `max_depth`.

    Depth is measured as the number of path components in the relative path from
    `root` to the file (for example, a file directly in `root` has depth 1).
    """
    tests = []
    root = root.resolve()
    for p in root.rglob("*"):
        if p.is_file():
            # ignore caches and pyc
            if "__pycache__" in p.parts:
                continue
            # limit by extension
            if p.suffix.lower() not in exts:
                continue
            # limit by depth
            try:
                rel = p.relative_to(root)
            except Exception:
                # if for some reason relative_to fails, skip
                continue
            depth = len(rel.parts)
            if depth > max_depth:
                continue
            tests.append(p)
    return sorted(tests)


def normalize_name(filename: str) -> str:
    """A conservative normalizer that:
    - converts hyphens to underscores
    - replaces multiple underscores/dashes with single underscore
    - makes lowercase
    - preserves extension
    """
    name, ext = os.path.splitext(filename)
    # If filename has multiple suffixes like .py.bak.txt, keep full suffix
    if "." in name:
        # rebuild ext to include all trailing parts
        parts = filename.split(".")
        name = ".".join(parts[:-1])
        ext = "." + parts[-1]
    new = name.replace("-", "_").lower()
    new = re.sub(r"[_]{2,}", "_", new)
    # normalize hyphens already handled
    return new + ext


def build_proposed_map(files: Iterable[Path], mapping_override: Dict[str, str]) -> Dict[Path, Path]:
    proposed: Dict[Path, Path] = {}
    for p in files:
        src_name = p.name
        if src_name in mapping_override:
            dst_name = mapping_override[src_name]
        else:
            dst_name = normalize_name(src_name)
        if dst_name != src_name:
            dst = p.with_name(dst_name)
            proposed[p] = dst
    return proposed


IMPORT_RE = re.compile(r"^(from|import)\s+([\w\.\-]+)", flags=re.MULTILINE)


def update_imports_in_file(path: Path, replace_map: Dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    # Replace module references only for simple cases: 'from X import' and 'import X'
    for old, new in replace_map.items():
        old_mod = module_name_from_filename(old)
        new_mod = module_name_from_filename(new)
        if old_mod == new_mod:
            continue
        # word-boundary replace for import uses
        text = re.sub(rf"\b{re.escape(old_mod)}\b", new_mod, text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def module_name_from_filename(filename: str) -> str:
    # remove extensions and multiple suffixes, then convert to module dotted form
    base = filename
    if filename.count("."):
        base = filename.split(".")[0]
    base = base.replace("-", "_")
    return base


def apply_renames(proposed: Dict[Path, Path], apply: bool, update_imports: bool) -> None:
    if not proposed:
        print("No renames proposed.")
        return

    print("Proposed renames:")
    for src, dst in proposed.items():
        print(f"  {src} -> {dst}")

    if not apply:
        print("\nDry-run mode: nothing changed. Use --apply to perform renames.")
        return

    # Ensure destination directories exist (they will be same dir)
    # Perform renames
    for src, dst in proposed.items():
        if dst.exists():
            print(f"Skipping rename, destination exists: {dst}")
            continue
        print(f"Renaming {src} -> {dst}")
        src.rename(dst)

    if update_imports:
        print("\nUpdating imports in project... (simple replacements)")
        # Build replace_map keyed by filename (old->new)
        replace_map = {s.name: d.name for s, d in proposed.items()}
        # Files to touch: all .py files under tests/ and package
        roots = [Path("tests"), Path("splurge_unittest_to_pytest")]
        touched: List[Tuple[Path, bool]] = []
        for r in roots:
            if not r.exists():
                continue
            for p in r.rglob("*.py"):
                if "__pycache__" in p.parts:
                    continue
                changed = update_imports_in_file(p, replace_map)
                touched.append((p, changed))
        for p, changed in touched:
            print(f"  {'M' if changed else ' '} {p}")


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalize and rename test files safely.")
    ap.add_argument("--apply", action="store_true", help="Perform renames; default is dry-run")
    ap.add_argument(
        "--update-imports", action="store_true", help="Attempt to update import statements to new module names"
    )
    ap.add_argument("--map-file", type=Path, help="CSV file with mapping: current,new")
    ap.add_argument("--root", type=Path, default=Path("tests"), help="Root folder to scan (default: tests)")
    ap.add_argument(
        "--ext", type=str, default=".py", help="Comma-separated list of file extensions to consider (default: .py)"
    )
    ap.add_argument("--max-depth", type=int, default=3, help="Maximum relative path depth to scan (default: 3)")
    args = ap.parse_args(argv)

    if args.map_file:
        mapping = load_map_from_csv(args.map_file)
    else:
        mapping = DEFAULT_MAP

    exts = [e if e.startswith(".") else "." + e for e in (s.strip() for s in args.ext.split(","))]
    files = discover_tests(args.root, exts, args.max_depth)
    proposed = build_proposed_map(files, mapping)
    apply_renames(proposed, apply=args.apply, update_imports=args.update_imports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
