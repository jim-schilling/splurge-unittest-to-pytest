"""Helpers to construct common import statement nodes.

Convenience helpers that build canonical :class:`libcst` import
statement nodes (for example the canonical ``import pytest`` statement).

These small, focused helpers keep import construction consistent across
the converter stages and make it easy to unit test import creation.

Publics:
    make_pytest_import_stmt: Create a canonical ``import pytest`` statement node.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter", "imports"]

# Associated domains for this module


def make_pytest_import_stmt() -> cst.SimpleStatementLine:
    """Create a SimpleStatementLine importing pytest."""
    return cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
