"""AST-based detection of unittest files.

This module provides robust detection of unittest files using AST analysis
rather than string heuristics, eliminating false positives and negatives.
"""

from .unittest_detector import UnittestFileDetector

__all__ = ["UnittestFileDetector"]
