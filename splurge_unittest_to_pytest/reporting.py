"""
Reporting utilities for splurge_unittest_to_pytest

Copyright (c) 2025 Jim Schilling
License: MIT
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any


def unified_diff_text(original: str, converted: str, *, path: Path | str | None = None) -> str:
    """Return a unified diff string between original and converted texts.

    Args:
        original: original source text
        converted: converted source text
        path: optional path to show in the diff header
    """
    fromlines = original.splitlines(keepends=True)
    tolines = converted.splitlines(keepends=True)
    a = str(path) if path is not None else "original"
    b = str(path) + " (converted)" if path is not None else "converted"
    diff = difflib.unified_diff(fromlines, tolines, fromfile=a, tofile=b)
    return "".join(diff)


def record_for_result(path: Path, result: Any, *, include_diff: bool = False) -> str:
    """Build an NDJSON record (string) for a ConversionResult-like object.

    The result is expected to have attributes: original_code, converted_code,
    has_changes, errors.
    """
    rec: dict[str, Any] = {
        "path": str(path),
        "changed": bool(getattr(result, "has_changes", False)),
        "errors": list(getattr(result, "errors", [])) or [],
    }

    # Small summary heuristics
    original = getattr(result, "original_code", "") or ""
    converted = getattr(result, "converted_code", "") or ""
    original_lines = original.splitlines()
    converted_lines = converted.splitlines()
    rec_summary: dict[str, Any] = {
        "lines_original": len(original_lines),
        "lines_converted": len(converted_lines),
        "lines_changed": abs(len(converted_lines) - len(original_lines)),
        "asserts_converted": sum(1 for line in converted_lines if line.strip().startswith("assert ")),
    }
    if include_diff and rec["changed"]:
        rec_summary["diff"] = unified_diff_text(original, converted, path=path)

    rec["summary"] = rec_summary
    return json.dumps(rec, ensure_ascii=False)
