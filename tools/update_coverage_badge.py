#!/usr/bin/env python3
"""Update README coverage badge from a coverage.xml file.

Reads reports/coverage.xml (or accepts an alternate path) and updates the
img.shields.io coverage badge in README.md. Intended to be run in CI after
running pytest --cov to produce coverage.xml.

Usage:
  python tools/update_coverage_badge.py --coverage reports/coverage.xml --readme README.md

This script is intentionally minimal and avoids external dependencies.
"""

from __future__ import annotations

import argparse
import re
from xml.etree import ElementTree as ET
from pathlib import Path
from typing import Optional


# Match existing coverage badge links. Accept both literal '%' and URL-encoded '%25'.
BADGE_RE = re.compile(
    r"(!\[Code Coverage\]\()(?P<url>https://img.shields.io/badge/coverage-)(?P<percent>[0-9]+)(?:%|%25)(?P<rest>[-A-Za-z0-9%_./?=&]*)\)"
)


def parse_coverage_percent(xml_path: Path) -> Optional[float]:
    if not xml_path.exists():
        return None
    root = ET.parse(xml_path).getroot()
    line_rate = root.attrib.get("line-rate")
    if line_rate is None:
        # Fallback: try package line-rate
        pkg = root.find("./packages/package")
        if pkg is not None:
            line_rate = pkg.attrib.get("line-rate")
    if line_rate is None:
        return None
    try:
        return float(line_rate) * 100.0
    except Exception:
        return None


def update_readme(readme_path: Path, percent: float) -> bool:
    text = readme_path.read_text(encoding="utf-8")
    pct_int = int(round(percent))

    def _repl(m: re.Match) -> str:
        # Preserve the rest of the URL; ensure we use percent-encoding for safety
        rest = m.group("rest") or ""
        # Use %25 in the badge URL to be URL-safe
        return f"{m.group(1)}{m.group('url')}{pct_int}%25{rest})"

    new_text, n = BADGE_RE.subn(_repl, text)
    if n > 0:
        readme_path.write_text(new_text, encoding="utf-8")
        return True

    # Badge not found: insert a new Coverage badge after the first header badges block
    lines = text.splitlines()
    badge_line = f"[![Code Coverage](https://img.shields.io/badge/coverage-{pct_int}%25-green.svg)](https://github.com/jim-schilling/splurge-unittest-to-pytest)"

    # Find the index after the last initial badge (heuristic: badges are in the first 10 lines)
    insert_idx = None
    for i, ln in enumerate(lines[:20]):
        if ln.strip().startswith("[!["):
            insert_idx = i

    if insert_idx is None:
        # No badge area found; prepend the badge at the top
        new_lines = [badge_line, "", *lines]
    else:
        # Insert after the last badge line we found
        # find the actual insertion point (after contiguous badge lines)
        j = insert_idx
        while j + 1 < len(lines) and lines[j + 1].strip().startswith("[!["):
            j += 1
        new_lines = [*lines[: j + 1], badge_line, *lines[j + 1 :]]

    readme_path.write_text("\n".join(new_lines), encoding="utf-8")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--coverage", default="reports/coverage.xml")
    p.add_argument("--readme", default="README.md")
    args = p.parse_args()

    cov = parse_coverage_percent(Path(args.coverage))
    if cov is None:
        print("Could not determine coverage percent from", args.coverage)
        raise SystemExit(2)

    updated = update_readme(Path(args.readme), cov)
    if not updated:
        print("Coverage badge not found or not updated in", args.readme)
        raise SystemExit(3)
    print(f"Updated coverage badge to {cov:.1f}% in {args.readme}")


if __name__ == "__main__":
    main()
