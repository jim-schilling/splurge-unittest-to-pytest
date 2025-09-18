"""Move top-level imports to the top of test modules.

This script parses each Python file under `tests/`, collects module-level
Import and ImportFrom nodes, and rewrites the file so that the module
docstring remains first, then any `from __future__` imports, then other
imports (deduplicated), followed by the rest of the original code with
the moved import lines removed.

It's conservative: only moves imports that are top-level (module-level AST nodes).
"""

from __future__ import annotations

import ast
from collections import OrderedDict
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]


def collect_top_level_import_lines(source: str) -> Tuple[List[Tuple[int, int, str]], str | None]:
    """Return list of (start_lineno, end_lineno, import_text) and module docstring."""
    tree = ast.parse(source)
    doc = ast.get_docstring(tree)
    imports: List[Tuple[int, int, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # ast nodes have lineno and end_lineno
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", start)
            if start is None:
                continue
            # extract text lines
            lines = source.splitlines()
            text = "\n".join(lines[start - 1 : end])
            imports.append((start, end, text))
    return imports, doc


def dedupe_ordered(lines: List[str]) -> List[str]:
    seen = OrderedDict()
    out: List[str] = []
    for line in lines:
        key = line.strip()
        if not key:
            continue
        if key in seen:
            continue
        seen[key] = True
        out.append(line)
    return out


def rewrite_file(path: Path) -> bool:
    src = path.read_text(encoding="utf8")
    imports, doc = collect_top_level_import_lines(src)
    if not imports:
        return False
    # sort imports by original order
    imports_sorted = sorted(imports, key=lambda t: t[0])
    future_lines: List[str] = []
    other_lines: List[str] = []
    for _, _, txt in imports_sorted:
        for line in txt.splitlines():
            if line.strip().startswith("from __future__"):
                future_lines.append(line.rstrip())
            else:
                other_lines.append(line.rstrip())

    future_lines = dedupe_ordered(future_lines)
    other_lines = dedupe_ordered(other_lines)

    # remove import lines from original source
    lines = src.splitlines()
    remove_ranges = []
    for s, e, _ in imports:
        remove_ranges.append((s, e))
    # produce new body lines skipping removed ranges
    out_lines: List[str] = []
    ranges_iter = iter(sorted(remove_ranges))
    try:
        cur_range = next(ranges_iter)
    except StopIteration:
        cur_range = None
    for i, line in enumerate(lines, start=1):
        if cur_range and cur_range[0] <= i <= cur_range[1]:
            if i == cur_range[1]:
                try:
                    cur_range = next(ranges_iter)
                except StopIteration:
                    cur_range = None
            continue
        out_lines.append(line)

    # rebuild file
    new_parts: List[str] = []
    if doc:
        # ensure docstring appears at top; we keep original docstring formatting
        new_parts.append(doc)
    if future_lines:
        new_parts.append("\n".join(future_lines))
    if other_lines:
        new_parts.append("\n".join(other_lines))
    # remaining code
    remaining = "\n".join(out_lines).lstrip()
    if remaining:
        new_parts.append(remaining)
    new_src = "\n\n".join(new_parts).rstrip() + "\n"
    path.write_text(new_src, encoding="utf8")
    return True


def main(*, argv: list[str] | None = None) -> int:
    # argv accepted for signature consistency with other tools; unused here
    fixed = 0
    for p in (ROOT / "tests").rglob("*.py"):
        try:
            if rewrite_file(p):
                print(f"fixed imports in {p}")
                fixed += 1
        except Exception as exc:
            print(f"error processing {p}: {exc}")
    print(f"done: fixed={fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=None))
