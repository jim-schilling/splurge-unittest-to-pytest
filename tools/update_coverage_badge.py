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


BADGE_RE = re.compile(
    r"(!\[Code Coverage\]\()(?P<url>https://img.shields.io/badge/coverage-)[0-9]+%25(?P<rest>[-A-Za-z0-9%_./?=&]*)\)"
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
    pct_str = f"{int(round(percent))}%"
    new_text, n = BADGE_RE.subn(lambda m: f"{m.group(1)}{m.group('url')}{pct_str}{m.group('rest')})", text)
    if n == 0:
        return False
    readme_path.write_text(new_text, encoding="utf-8")
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
