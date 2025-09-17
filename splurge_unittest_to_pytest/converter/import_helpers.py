"""Helpers to construct common import statement nodes.

Exports convenience helpers that build canonical :class:`libcst` import
statement nodes (for example the canonical ``import pytest`` statement)
so import construction remains consistent across the injector code.
"""

from __future__ import annotations

import libcst as cst

DOMAINS = ["converter", "imports"]

# Associated domains for this module


def make_pytest_import_stmt() -> cst.SimpleStatementLine:
    """Create a SimpleStatementLine importing pytest."""
    return cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
