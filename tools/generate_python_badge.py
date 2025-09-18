#!/usr/bin/env python3
"""Generate or update a Python versions badge in README from pyproject.toml.

The script reads `pyproject.toml` to determine supported Python versions (from
classifiers and requires-python) and updates a shields.io style badge in
`README.md` that lists supported versions.

Usage:
  python tools/generate_python_badge.py --pyproject pyproject.toml --readme README.md
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
import tomllib


BADGE_PY_RE = re.compile(r"(!\[Python Versions\]\()(https://img.shields.io/badge/python-)[^\)]+\)")


def read_pyproject(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def extract_versions(pyproject: dict) -> list[str]:
    # Prefer explicit classifiers if present
    classifiers = pyproject.get("project", {}).get("classifiers", [])
    versions = []
    for c in classifiers:
        if c.startswith("Programming Language :: Python :: "):
            v = c.split("::")[-1].strip()
            if v and v not in ("3",):
                versions.append(v)
    # Fallback to requires-python
    if not versions:
        req = pyproject.get("project", {}).get("requires-python")
        if req:
            # crude parse: expecting formats like >=3.10,<3.14
            parts = re.findall(r"3\.\d+", req)
            versions = sorted(set(parts))
    return versions


def update_readme(readme: Path, versions: list[str]) -> bool:
    if not versions:
        return False
    label = "%20%7C%20".join(versions)
    badge = f"[![Python Versions](https://img.shields.io/badge/python-{label}-blue.svg)](https://www.python.org/downloads/)"
    text = readme.read_text(encoding="utf-8")
    if BADGE_PY_RE.search(text):
        new_text = BADGE_PY_RE.sub(badge, text)
    else:
        # Insert at top after the first heading
        new_text = text.replace("# Splurge unittest-to-pytest\n\n", f"# Splurge unittest-to-pytest\n\n{badge}\n")
    readme.write_text(new_text, encoding="utf-8")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pyproject", default="pyproject.toml")
    p.add_argument("--readme", default="README.md")
    args = p.parse_args()

    pj = read_pyproject(Path(args.pyproject))
    versions = extract_versions(pj)
    if not versions:
        print("No python versions found in pyproject.toml")
        raise SystemExit(2)
    updated = update_readme(Path(args.readme), versions)
    if not updated:
        print("Failed to update README with python badge")
        raise SystemExit(3)
    print("Updated README with Python versions:", ",".join(versions))


if __name__ == "__main__":
    main()
