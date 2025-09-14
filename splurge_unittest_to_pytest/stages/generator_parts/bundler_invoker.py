from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import libcst as cst

from .namedtuple_bundler import bundle_named_locals


def safe_bundle_named_locals(
    out_classes: Dict[str, Any], existing_top_names: Set[str], full: bool = False
) -> Tuple[List[cst.BaseStatement], Set[str], Dict[str, str]]:
    """Call bundle_named_locals but be tolerant to exceptions.

    The original `generator.py` wrapped the bundler call in a try/except
    to avoid crashing fixture generation if the heuristic code encounters
    an unexpected input. This preserves that behavior in one place so
    it's easier to unit-test and reason about.
    """
    try:
        nodes, needs, mapping = bundle_named_locals(out_classes, existing_top_names)
        # Always return the full 3-tuple. The `full` flag is kept for
        # backward compatibility but callers should expect a mapping
        # (possibly empty) as the third return value.
        if not mapping:
            mapping = {}
        return nodes, needs, mapping
    except Exception:
        # On error, return empty structures for all three expected values
        return [], set(), {}
