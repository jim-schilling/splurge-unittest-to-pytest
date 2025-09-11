"""Namespace package for converter decomposition.

This package is intentionally a skeleton initially. Implementation will be
migrated here in small, safe steps to keep changes easy to review.
"""

from __future__ import annotations

from importlib import util
from pathlib import Path
import sys

# Re-export a couple of legacy public names from the monolithic
# `splurge_unittest_to_pytest/converter.py` to preserve existing import sites
# while we decompose the implementation into smaller modules.
_legacy_path = Path(__file__).resolve().parent.parent / "converter.py"
_legacy_name = "splurge_unittest_to_pytest._legacy_converter"
if _legacy_path.exists():
    spec = util.spec_from_file_location(_legacy_name, str(_legacy_path))
    if spec and spec.loader:
        legacy = util.module_from_spec(spec)
        # Ensure module is importable under a stable name for pickling/debugging
        sys.modules[_legacy_name] = legacy
        spec.loader.exec_module(legacy)
        # Re-export the most commonly used public names to maintain compatibility
        try:
            SelfReferenceRemover = legacy.SelfReferenceRemover
        except AttributeError:
            pass
        try:
            UnittestToPytestTransformer = legacy.UnittestToPytestTransformer
        except AttributeError:
            pass

__all__ = [
    "utils",
    "assertions",
    "fixtures",
    "raises",
    "imports",
    "core",
    "SelfReferenceRemover",
    "UnittestToPytestTransformer",
]
