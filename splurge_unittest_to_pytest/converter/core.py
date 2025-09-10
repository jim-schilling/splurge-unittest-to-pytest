"""Thin core wrapper for converter public API.

Initially this will re-export existing public symbols from the monolithic
`converter.py` to minimize behavior changes. We'll migrate implementations
incrementally.
"""
from __future__ import annotations

# Re-export commonly used public symbols to preserve the public API while we
# decompose the implementation into smaller modules.
from ..converter.utils import SelfReferenceRemover, normalize_method_name

__all__ = ["SelfReferenceRemover", "normalize_method_name"]
