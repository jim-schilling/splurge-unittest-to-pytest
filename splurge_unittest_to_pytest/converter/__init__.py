"""Namespace package for converter decomposition.

This package is intentionally a skeleton initially. Implementation will be
migrated here in small, safe steps to keep changes easy to review.
"""

from __future__ import annotations

from .helpers import SelfReferenceRemover

__all__ = [
    "utils",
    "assertions",
    "fixtures",
    "raises",
    "imports",
    "core",
    "SelfReferenceRemover",
]

__all__ = [
    "utils",
    "assertions",
    "fixtures",
    "raises",
    "imports",
    "core",
    "SelfReferenceRemover",
    # legacy transformer intentionally not re-exported; prefer staged pipeline
]
