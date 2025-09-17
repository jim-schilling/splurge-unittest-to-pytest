"""Rename test modules based on their DOMAINS metadata.

Usage:
  python tools/rename_tests_by_domains.py [--root tests] [--apply]

Default is a dry-run which prints "original | proposed". When --apply is used
the script will perform os.rename and print "[original] -> [new]" for each
rename.

Naming rule:
  test_<domain1>_<domain2>_<NNN>.py
where domains come from the module-level DOMAINS list (order preserved) and
NNN is a zero-padded 3-digit sequence per prefix.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


def read_domains_from_file(path: Path) -> List[str]:
    """Return the module-level DOMAINS as a list of strings, or empty list."""
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return []
    try:
        tree = ast.parse(src)
    except Exception:
        tree = None
    if tree is not None:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "DOMAINS":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            out: List[str] = []
                            for el in node.value.elts:
                                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                                    out.append(el.value)
                            return out
                        return []
    # fallback: regex
    m = re.search(r"^DOMAINS\s*=\s*\[(.*?)\]", src, re.S | re.M)
    if m:
        items = re.findall(r"['\"](.*?)['\"]", m.group(1))
        return items
    return []


def slug_domain_list(domains: List[str]) -> str:
    # join with underscore and sanitize to [a-z0-9_]
    joined = "_".join(d.strip().lower() for d in domains if d)
    # replace non-alnum with underscore
    cleaned = re.sub(r"[^a-z0-9_]+", "_", joined)
    # collapse multiple underscores
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        return "misc"
    return cleaned


def build_proposals(root: Path) -> List[Tuple[Path, Path]]:
    """Scan test files and return a list of (original_path, proposed_path).

    Proposed filenames are placed in the same directory as original files.
    Sequence numbers are assigned per prefix across the whole scan.
    """
    files: List[Path] = sorted(root.rglob("*.py"))
    # gather list of (file, prefix)
    groups: Dict[str, List[Path]] = {}
    mapping: Dict[Path, str] = {}
    for f in files:
        # Skip files in helper directories (they are package modules used by tests)
        # and skip non-test files (we only want to rename files that already
        # follow the `test_` prefix). This prevents renaming helpers and
        # special files like conftest.py.
        if any(part.lower() == "helpers" for part in f.parts):
            continue
        if not f.name.startswith("test_"):
            # skip conftest.py and other non-test modules
            continue
        domains = read_domains_from_file(f)
        prefix = "test_" + slug_domain_list(domains)
        mapping[f] = prefix
        groups.setdefault(prefix, []).append(f)

    proposals: List[Tuple[Path, Path]] = []
    # for each prefix, sort files to make deterministic sequence
    for prefix, flist in sorted(groups.items()):
        flist_sorted = sorted(flist, key=lambda p: str(p).lower())
        for idx, f in enumerate(flist_sorted, start=1):
            seq = f"{idx:03d}"
            new_name = f"{prefix}_{seq}.py"
            new_path = f.with_name(new_name)
            proposals.append((f, new_path))
    return proposals


def show_dry_run(proposals: List[Tuple[Path, Path]]) -> None:
    print("DRY RUN - original | proposed")
    for orig, prop in proposals:
        print(f"{orig} | {prop.name}")


def apply_renames(proposals: List[Tuple[Path, Path]]) -> None:
    # first ensure no target collisions outside of the rename set
    targets = {p for _, p in proposals}
    for t in targets:
        if t.exists() and t not in [o for o, _ in proposals]:
            print(f"ERROR: target exists and is not being renamed: {t}")
            raise SystemExit(1)

    for orig, prop in proposals:
        if orig == prop:
            continue
        # if prop exists and is one of the originals, it's fine; perform rename
        print(f"[{orig}] -> [{prop}]")
        prop.parent.mkdir(parents=True, exist_ok=True)
        os.replace(str(orig), str(prop))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rename test modules based on DOMAINS metadata")
    p.add_argument("--root", default="tests", help="Root tests directory to scan")
    p.add_argument("--apply", action="store_true", help="Apply the renames (default is dry-run)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"Test root not found: {root}")
        raise SystemExit(1)
    proposals = build_proposals(root)
    if not args.apply:
        show_dry_run(proposals)
        print(f"\nProposals: {len(proposals)} (use --apply to perform)")
        return
    # apply
    apply_renames(proposals)


if __name__ == "__main__":
    main()
