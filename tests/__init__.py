"""Test package marker for top-level tests package.

This file makes `tests` importable as a package so that imports like
`from tests.unit.helpers import ...` work during test collection.
"""

__all__ = []
