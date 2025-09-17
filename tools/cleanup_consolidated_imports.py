"""Cleanup duplicate imports in consolidated test modules.

This script visits each .py file under a target root (default: tests/consolidated)
and removes later import statements that introduce names already bound earlier in the
module. It keeps the first import that defines a given name and drops subsequent
imports that would shadow or rebind that name.

This is a best-effort cleanup to help linters (F811) after many fragments were
merged into single consolidated modules.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Set


def defined_names_from_import(node: ast.stmt) -> Set[str]:
    names: Set[str] = set()
    if isinstance(node, ast.Import):
        for a in node.names:
            names.add(a.asname if a.asname else a.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        # from x import * -> we can't reason, keep it
        for a in node.names:
            if a.name == "*":
                names.add("*")
            else:
                names.add(a.asname if a.asname else a.name)
    return names


def process_file(path: Path) -> bool:
    src = path.read_text(encoding="utf8")
    try:
        mod = ast.parse(src)
    except SyntaxError:
        return False
    seen: Set[str] = set()
    new_body: list[ast.stmt] = []
    changed = False
    for node in mod.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = defined_names_from_import(node)
            # if wildcard import present, keep it and reset seen to be conservative
            if "*" in names:
                new_body.append(node)
                seen.update(names - {"*"})
                continue
            # check if any name overlaps seen; if so, drop the node
            if any(n in seen for n in names):
                changed = True
                # skip this import (we keep earlier one)
                continue
            seen.update(names)
            new_body.append(node)
        else:
            new_body.append(node)

    if changed:
        mod.body = new_body
        try:
            new_src = ast.unparse(mod)
        except Exception:
            return False
        path.write_text(new_src, encoding="utf8")
    return changed


def main(root: str | None = None) -> int:
    r = Path(root) if root else Path("tests/consolidated")
    if not r.exists():
        print("root not found:", r)
        return 2
    total = 0
    changed = 0
    for p in r.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        total += 1
        if process_file(p):
            changed += 1
            print("cleaned", p)
    print(f"processed {total} files, changed {changed}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(None if len(sys.argv) == 1 else sys.argv[1]))
