"""Move module-level DOMAINS assignments to the top of modules.

This script scans Python files in the `splurge_unittest_to_pytest` package, finds
any `DOMAINS = [ ... ]` assignments, and moves them to just after the module
imports (or top if none). It defaults to a dry-run; pass `--apply` to write files.

Usage:
    python tools/move_domains.py --dry-run
    python tools/move_domains.py --apply

This is conservative: it only moves simple assignments where the RHS is a
literal list of string literals.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "splurge_unittest_to_pytest"


def find_domains_assignment(node: ast.AST) -> Tuple[int, int, ast.Assign] | None:
    """Return (lineno, end_lineno, assign_node) if a DOMAINS = [...] found at module level.

    Only matches simple assignments to a Name 'DOMAINS' with a List of Str ast nodes.
    """
    for n in node.body:
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name) and target.id == "DOMAINS":
                    # ensure value is list of strings
                    if isinstance(n.value, ast.List) and all(
                        isinstance(elt, ast.Constant) and isinstance(elt.value, str) for elt in n.value.elts
                    ):
                        return n.lineno, getattr(n, "end_lineno", n.lineno), n
    return None


def find_import_end_lineno(node: ast.AST) -> int:
    """Return the line after the last import in the module (or 1).

    We'll place DOMAINS after the import block.
    """
    last_import = 0
    doc_end = 0
    # find module docstring node if present
    for n in node.body:
        if (
            isinstance(n, ast.Expr)
            and isinstance(getattr(n, "value", None), ast.Constant)
            and isinstance(n.value.value, str)
        ):
            doc_end = getattr(n, "end_lineno", n.lineno)
            break

    for n in node.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            last_import = getattr(n, "end_lineno", n.lineno)

    # insertion point is after the last import or after the docstring, whichever is later
    return max(doc_end, last_import)


def process_file(path: Path) -> Tuple[bool, str]:
    """Analyze file and return (would_change, preview_text).

    If a change is needed, `would_change` is True and `preview_text` shows the proposed content.
    """
    src = path.read_text(encoding="utf-8")
    try:
        mod = ast.parse(src)
    except SyntaxError:
        return False, "(syntax error parsing file)"

    # find module docstring node (if any)
    # find DOMAINS assignment
    found = find_domains_assignment(mod)
    if not found:
        return False, "(no DOMAINS assignment)"

    a_lineno, a_end, assign_node = found
    import_end = find_import_end_lineno(mod)
    # compute new source
    lines = src.splitlines()
    assign_block = lines[a_lineno - 1 : a_end]
    # remove original block
    del lines[a_lineno - 1 : a_end]
    # adjust insertion index because we've removed lines before the original import_end
    removed_count = a_end - a_lineno + 1
    if a_lineno <= import_end:
        insert_at = import_end - removed_count
    else:
        insert_at = import_end
    # if there is a module docstring, imports may start after it; we put after imports
    lines.insert(insert_at, "")
    for i, line in enumerate(assign_block):
        lines.insert(insert_at + 1 + i, line)

    new_src = "\n".join(lines) + "\n"
    return True, new_src


def find_files() -> List[Path]:
    return list(PKG.rglob("*.py"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Write changes")
    p.add_argument("--show", type=str, default="", help="Preview a single file's proposed content")
    p.add_argument("--limit", type=int, default=0, help="Limit number of files to process")
    args = p.parse_args()

    if args.show:
        path = Path(args.show)
        if not path.exists():
            print(f"Not found: {path}")
            return 2
        ok, new = process_file(path)
        if not ok:
            print(new)
            return 0
        print(new)
        return 0

    files = find_files()
    changed = 0
    for f in sorted(files):
        ok, new = process_file(f)
        if ok:
            changed += 1
            print(f"Will update: {f}")
            if args.apply:
                f.write_text(new, encoding="utf-8")
                print(f"WROTE: {f}")
        if args.limit and changed >= args.limit:
            break

    print(f"Scanned {len(files)} files. Proposed updates: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
