from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import libcst as cst

from .namedtuple_bundler import bundle_named_locals

DOMAINS = ["generator", "bundles"]


# Associated domains for this module


def safe_bundle_named_locals(
    out_classes: Dict[str, Any], existing_top_names: Set[str], full: bool = False
) -> Tuple[List[cst.BaseStatement], Set[str], Dict[str, str]]:
    """Safely invoke the named-local bundler and return a normalized result.

    Calls :func:`bundle_named_locals` and returns ``(nodes, needs, mapping)``.
    Any exception during bundling is caught and an empty result is returned
    for robustness in the generator pipeline.
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
