"""Run conversion on samples and update goldens when conversion output differs.

This script loads each sample unittest file under tests/data/samples/*.txt,
converts it with the public API, and writes a golden in tests/goldens/ matching
filename pattern. It shows diffs for review and updates the golden files.
"""

from __future__ import annotations

import difflib
import pathlib
from typing import List

from splurge_unittest_to_pytest.main import convert_string

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "tests" / "data" / "samples"
GOLDENS = ROOT / "tests" / "goldens"


def run():
    updated: List[pathlib.Path] = []
    for p in sorted(SAMPLES.glob("*.txt")):
        src = p.read_text()
        res = convert_string(src)
        out = res.converted_code
        gold_name = p.stem + ".golden"
        gold_path = GOLDENS / gold_name
        if gold_path.exists():
            gold = gold_path.read_text()
        else:
            gold = ""
        if out != gold:
            print(f"Updating golden: {gold_path}")
            # show short unified diff
            diff = difflib.unified_diff(
                gold.splitlines(keepends=True), out.splitlines(keepends=True), fromfile=str(gold_path), tofile=str(p)
            )
            print("".join(list(diff))[:10000])
            gold_path.write_text(out)
            updated.append(gold_path)
    if updated:
        print(f"Updated {len(updated)} golden(s)")
    else:
        print("No goldens changed")


if __name__ == "__main__":
    run()
