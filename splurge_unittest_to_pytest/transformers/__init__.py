"""Transformer modules for CST-based code transformations.

Each transformer module contains the libcst-based transformation logic
for converting unittest patterns to pytest equivalents.
"""

from .unittest_transformer import (
    HistoricalUnittestToPytestTransformer,
    UnittestToPytestCSTTransformer,
)
from .unittest_transformer import (
    UnittestToPytestTransformer as UnittestToPytestShim,
)

# Public API: prefer the CST-based transformer as the canonical `UnittestToPytestTransformer`
# while also exposing the shim under an explicit name for compatibility.
UnittestToPytestTransformer = UnittestToPytestCSTTransformer
__all__ = [
    "UnittestToPytestTransformer",
    "UnittestToPytestCSTTransformer",
    "UnittestToPytestShim",
    "HistoricalUnittestToPytestTransformer",
]
