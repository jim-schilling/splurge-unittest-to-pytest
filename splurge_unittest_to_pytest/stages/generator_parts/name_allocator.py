from __future__ import annotations

from typing import Set

DOMAINS = ["generator", "naming"]


# Associated domains for this module


def choose_local_name(base: str, taken: Set[str]) -> str:
    """Deterministically pick a unique local name by appending a numeric
    suffix when needed. Reserves the chosen name in ``taken``.

    This mirrors the logic previously embedded in
    `stages/generator.py` and is intentionally small and well-tested.
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

    The allocator returns the base name on first use and appends an
    incrementing suffix (``_2``, ``_3``, ...) for subsequent allocations
    using the same base.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def allocate(self, base: str) -> str:
        count = self._counts.get(base, 0) + 1
        self._counts[base] = count
        return f"{base}_{count}" if count > 1 else base
