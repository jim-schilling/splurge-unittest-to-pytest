"""Fix inlined test file collisions and remove __pycache__ directories.

This is a utility originally used against `tmp/inlined_consolidated/tests` to avoid
pytest import collisions when multiple files end up with the same basename.

It performs two actions:
- remove any __pycache__ directories under the given root
- find duplicate basenames and rename the later ones by appending a unique suffix

Example:
  python tools/fix_inlined_collisions.py --root tmp/inlined_consolidated/tests
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def remove_pycache(root: Path) -> int:
    removed = 0
    for p in root.rglob("__pycache__"):
        try:
            for child in p.iterdir():
                child.unlink()
            p.rmdir()
            removed += 1
        except Exception:
            # best-effort
            pass
    return removed


def rename_collisions(root: Path) -> list[tuple[Path, Path]]:
    # find all .py files and group by basename
    by_base: dict[str, list[Path]] = defaultdict(list)
    for p in root.rglob("*.py"):
        by_base[p.name].append(p)

    renames: list[tuple[Path, Path]] = []
    for name, paths in by_base.items():
        if len(paths) <= 1:
            continue
        # sort to have deterministic ordering
        paths = sorted(paths)
        # keep first, rename the rest
        for idx, p in enumerate(paths[1:], start=1):
            parent = p.parent.name
            base_stem = p.stem
            candidate = f"{base_stem}__{parent}_{idx:02d}.py"
            target = p.with_name(candidate)
            # if target exists, pick a unique name by appending numeric suffix
            i = 1
            while target.exists():
                candidate = f"{base_stem}__{parent}_{idx:02d}_{i:02d}.py"
                target = p.with_name(candidate)
                i += 1
            p.rename(target)
            renames.append((p, target))
    return renames


def main(*, root: str | None = None) -> int:
    r = Path(root) if root else Path("tmp/inlined_consolidated/tests")
    if not r.exists():
        print("root not found:", r)
        return 2
    removed = remove_pycache(r)
    renames = rename_collisions(r)
    print(f"Removed __pycache__ dirs: {removed}")
    print(f"Performed renames: {len(renames)}")
    for src, dst in renames:
        print(f"{src} -> {dst}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", help="root to fix", default="tmp/inlined_consolidated/tests")
    args = ap.parse_args()
    # call using keyword to match keyword-only signature
    raise SystemExit(main(root=args.root))
