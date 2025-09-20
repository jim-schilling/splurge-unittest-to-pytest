"""Fix plain-text leading headers by wrapping them as module docstrings.

This scans .py files under a path and if the file starts with a paragraph of
plain English (not a comment, shebang, import, def, class, or existing
docstring) it wraps that paragraph in triple quotes so the module parses.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

CODE_START_RE = re.compile(r'^(#|from\b|import\b|def\b|class\b|@|\'\'\'|"""|#!)')


def find_py_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        # skip virtualenvs, backups and tools themselves
        if any(part in ("venv", ".venv", "backups", ".git") for part in p.parts):
            continue
        yield p


def has_docstring(text: str) -> bool:
    s = text.lstrip()
    return s.startswith(('"""', "'''"))


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text:
        return False
    lines = text.splitlines()
    # find first non-empty line index
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines):
        return False
    first = lines[idx].lstrip()
    if CODE_START_RE.match(first):
        return False
    if has_docstring(text):
        # Coalesce any plain-text paragraph between the docstring end
        # and the first code-like line into the existing docstring.
        start = idx
        # identify delimiter and end of docstring
        delim = '"""' if lines[start].lstrip().startswith('"""') else "'''"
        # if opening line also contains closing delimiter, single-line docstring
        open_line = lines[start]
        if open_line.count(delim) >= 2:
            doc_end = start
        else:
            doc_end = start + 1
            while doc_end < len(lines) and delim not in lines[doc_end]:
                doc_end += 1
            if doc_end >= len(lines):
                return False

        # collect plain-text paragraph after doc_end until blank or code-like line
        j = doc_end + 1
        para = []
        while j < len(lines):
            stripped = lines[j].strip()
            if not stripped:
                break
            if CODE_START_RE.match(stripped):
                break
            para.append(lines[j].rstrip())
            j += 1

        if not para:
            return False

        # Insert para into the docstring before the closing delimiter
        # If closing delimiter is on its own line, insert before that line
        if lines[doc_end].strip() == delim:
            new_lines = lines[:doc_end] + [""] + para + [""] + lines[doc_end:]
        else:
            # closing delimiter is on same line as other text -> expand to multiline
            # extract content before and after delimiter
            before = lines[:start]
            # build a new multiline docstring
            new_doc = [delim, ""] + para + [""] + [delim]
            new_lines = before + new_doc + lines[doc_end + 1 :]

        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"coalesced header into docstring in {path}")
        return True

    # No docstring: collect paragraph lines until blank or code-looking line
    para = []
    j = idx
    while j < len(lines):
        line = lines[j]
        stripped = line.strip()
        if not stripped:
            break
        if CODE_START_RE.match(stripped):
            break
        para.append(line.rstrip())
        j += 1

    if not para:
        return False

    doc = ['"""'] + [""] + [line for line in para] + [""] + ['"""']
    new_lines = lines[:idx] + doc + lines[j:]
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"wrapped header in {path}")
    return True


def main(*, argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("root", nargs="?", default="tests", help="root folder to scan")
    args = p.parse_args(argv)
    root = Path(args.root)
    fixed = 0
    for f in find_py_files(root):
        try:
            if fix_file(f):
                fixed += 1
        except Exception as e:
            print(f"error processing {f}: {e}")
    print(f"done: fixed={fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=None))
