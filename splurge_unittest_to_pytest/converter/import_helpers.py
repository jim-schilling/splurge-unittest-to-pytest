"""Small helpers for import statement creation used by imports.py."""
from __future__ import annotations

import libcst as cst


def make_pytest_import_stmt() -> cst.SimpleStatementLine:
    """Create a SimpleStatementLine importing pytest."""
    return cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
