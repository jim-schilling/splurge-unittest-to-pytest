"""Safe wrapper around the named-local bundler.

The bundler may raise exceptions for complex inputs; this small wrapper
ensures the generator remains robust by catching errors and returning a
well-formed, empty result on failure. It mirrors the production API but
is defensive for tests.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import libcst as cst

from .namedtuple_bundler import bundle_named_locals

DOMAINS = ["generator", "bundles"]


# Associated domains for this module


def safe_bundle_named_locals(
    out_classes: Dict[str, Any], existing_top_names: Set[str], full: bool = False
) -> Tuple[List[cst.BaseStatement], Set[str], Dict[str, str]]:
    """Invoke the named-local bundler with a defensive wrapper.

    Returns a 3-tuple ``(nodes, needs, mapping)`` by delegating to
    :func:`bundle_named_locals`. Any exceptions raised by the bundler are
    caught and an empty result is returned to keep the generator stage
    robust.
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
