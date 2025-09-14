from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import libcst as cst


@dataclass
class SimpleFixtureSpec:
    name: str
    value_expr: Optional[cst.BaseExpression]
    cleanup_statements: list[Any]
    yield_style: bool


def _is_dir_like(name: str) -> bool:
    return any(k in name for k in ("dir", "path", "temp"))
