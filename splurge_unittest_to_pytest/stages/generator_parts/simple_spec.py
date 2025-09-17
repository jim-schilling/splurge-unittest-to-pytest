from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import libcst as cst

DOMAINS = ["generator"]


# Associated domains for this module


@dataclass
class SimpleFixtureSpec:
    name: str
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: list[Any]
    yield_style: bool


def _is_dir_like(name: str) -> bool:
    """Return True if the name looks directory-like.

    Checks for common substrings used for directory/path-like names.
    """
    return any(k in name for k in ("dir", "path", "temp"))
