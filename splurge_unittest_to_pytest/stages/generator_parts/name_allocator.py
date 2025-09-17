from __future__ import annotations

from typing import Set

DOMAINS = ["generator", "naming"]


# Associated domains for this module


def choose_local_name(base: str, taken: Set[str]) -> str:
    """Pick a unique local name based on ``base`` and reserve it.

    If ``base`` is already present in ``taken``, a numeric suffix is
    appended (``_1``, ``_2``, ...) until a free name is found. The
    chosen name is inserted into ``taken`` before returning.
    """
    if base not in taken:
        taken.add(base)
        return base
    suffix = 1
    while True:
        candidate = f"{base}_{suffix}"
        if candidate not in taken:
            taken.add(candidate)
            return candidate
        suffix += 1


class NameAllocator:
    """Deterministic allocator for generated fixture names.

    On first allocation the base name is returned. Subsequent allocations
    for the same base append an incrementing numeric suffix ("_2",
    "_3", ...).
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def allocate(self, base: str) -> str:
        count = self._counts.get(base, 0) + 1
        self._counts[base] = count
        return f"{base}_{count}" if count > 1 else base
