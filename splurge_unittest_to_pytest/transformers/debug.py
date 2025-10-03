"""Small debug helpers for transformers.

Provides a DEV/CI gate to re-raise transformation exceptions when
`SPLURGE_TRANSFORM_DEBUG` is truthy.
"""

from __future__ import annotations

import os


def get_transform_debug() -> bool:
    v = os.getenv("SPLURGE_TRANSFORM_DEBUG", "")
    return v in {"1", "true", "True"}


def maybe_reraise(exc: BaseException) -> None:
    """Re-raise the exception when debug is enabled, otherwise do nothing."""
    if get_transform_debug():
        raise exc
