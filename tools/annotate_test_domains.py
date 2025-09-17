#!/usr/bin/env python3
"""Annotate test modules with DOMAINS aggregated from imported package modules.

For each .py under tests/, collect imports that reference the project package
(`splurge_unittest_to_pytest.*`). For each referenced module, read its
`DOMAINS` assignment (a literal list of strings) and aggregate those values.
Then insert or update a `DOMAINS = [...]` assignment right after the import
block (or after the module docstring if no imports).

Usage:
    python tools/annotate_test_domains.py --dry-run
    python tools/annotate_test_domains.py --apply

This is conservative: it only reads literal `DOMAINS = [...]` lists from the
package modules and only updates test files by simple textual edits.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "splurge_unittest_to_pytest"
TESTS = ROOT / "tests"


def find_domains_assignment_in_module(src: str) -> List[str]:
    try:
        mod = ast.parse(src)
    except SyntaxError:
        return []
    for n in mod.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "DOMAINS":
                    if isinstance(n.value, ast.List):
                        vals: List[str] = []
                        for elt in n.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                vals.append(elt.value)
                        return vals
    return []


def module_name_to_path(module_name: str) -> Path | None:
    # module_name expected to start with 'splurge_unittest_to_pytest'
    parts = module_name.split(".")
    if not parts:
        return None
    if parts[0] != "splurge_unittest_to_pytest":
        return None
    # if module is the package root, return package __init__.py
    if len(parts) == 1:
        candidate_pkg_init = PKG / "__init__.py"
        if candidate_pkg_init.exists():
            return candidate_pkg_init
        return None

    rel = Path(*parts[1:])
    # check for file module (e.g. splurge_unittest_to_pytest.module.py)
    try:
        candidate_py = PKG / rel.with_suffix(".py")
    except Exception:
        candidate_py = PKG / (rel.as_posix() + ".py")
    if candidate_py.exists():
        return candidate_py
    # check for package __init__.py in subpackage
    candidate_pkg_init = PKG / rel / "__init__.py"
    if candidate_pkg_init.exists():
        return candidate_pkg_init
    return None


def collect_imported_package_modules(src: str) -> Set[str]:
    try:
        mod = ast.parse(src)
    except SyntaxError:
        return set()
    imported: Set[str] = set()
    for n in ast.walk(mod):
        if isinstance(n, ast.Import):
            for alias in n.names:
                name = alias.name
                if name.startswith("splurge_unittest_to_pytest"):
                    imported.add(name)
        elif isinstance(n, ast.ImportFrom):
            modname = n.module
            if modname and modname.startswith("splurge_unittest_to_pytest"):
                imported.add(modname)
    return imported


def find_import_block_end(src: str) -> int:
    # return index in lines after last import (0-based index where to insert)
    try:
        mod = ast.parse(src)
    except SyntaxError:
        return 0
    last_import = 0
    doc_end = 0
    for n in mod.body:
        if (
            isinstance(n, ast.Expr)
            and isinstance(getattr(n, "value", None), ast.Constant)
            and isinstance(n.value.value, str)
        ):
            doc_end = getattr(n, "end_lineno", n.lineno)
            break
    for n in mod.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            last_import = getattr(n, "end_lineno", n.lineno)
    # return a 0-based index for lines list
    insert_after = max(doc_end, last_import)
    return insert_after


def process_test_file(path: Path) -> Tuple[bool, str]:
    src = path.read_text(encoding="utf-8")
    imported = collect_imported_package_modules(src)
    domains: Set[str] = set()
    for modname in sorted(imported):
        mp = module_name_to_path(modname)
        if not mp:
            continue
        msrc = mp.read_text(encoding="utf-8")
        vals = find_domains_assignment_in_module(msrc)
        for v in vals:
            domains.add(v)
    # prepare assignment text
    # sort domains A-Z case-insensitive for stable ordering
    dom_list = sorted(domains, key=lambda s: s.lower())
    assign_lines = [f"DOMAINS = {repr(dom_list)}", ""]

    # check if file already has DOMAINS assignment
    try:
        mod = ast.parse(src)
    except SyntaxError:
        return False, "(syntax error)"
    existing_node = None
    for n in mod.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "DOMAINS":
                    existing_node = n
                    break
        if existing_node:
            break

    lines = src.splitlines()
    if existing_node:
        a_lineno = existing_node.lineno
        a_end = getattr(existing_node, "end_lineno", a_lineno)
        # replace existing block with new assignment
        new_lines = lines[: a_lineno - 1] + assign_lines + lines[a_end:]
        new_src = "\n".join(new_lines) + "\n"
        changed = new_src != src
        return changed, new_src
    else:
        insert_after = find_import_block_end(src)
        # insert at that line index (lines are 0-based; insert_after is count of lines to keep)
        new_lines = lines[:insert_after] + [""] + assign_lines + lines[insert_after:]
        new_src = "\n".join(new_lines) + "\n"
        changed = new_src != src
        return changed, new_src


def find_test_files() -> List[Path]:
    if not TESTS.exists():
        return []
    return [p for p in TESTS.rglob("*.py") if "__pycache__" not in p.parts]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    files = find_test_files()
    changed = 0
    for f in sorted(files):
        ok, new = process_test_file(f)
        if ok:
            print(f"Will update: {f}")
            changed += 1
            if args.apply:
                f.write_text(new, encoding="utf-8")
                print(f"WROTE: {f}")
        if args.limit and changed >= args.limit:
            break
    print(f"Scanned {len(files)} test files. Proposed updates: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
