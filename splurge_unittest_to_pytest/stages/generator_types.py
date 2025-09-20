from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import libcst as cst

DOMAINS = ["stages", "generator", "types"]


@dataclass
class FixtureSpec:
    name: str
    # value_expr can legitimately be None when collector recorded no value
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: list[Any]
    yield_style: bool
    local_value_name: Optional[str] = None
    """Data container describing a generated fixture.

    Fields mirror the earlier inlined FixtureSpec used by the generator.
    """


__all__ = ["FixtureSpec"]
