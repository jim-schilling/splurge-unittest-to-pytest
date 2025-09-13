class NameAllocator:
    """Trivial name allocator for generated fixtures.

    This scaffolding provides a deterministic name for a requested base
    name and an incrementing suffix if needed.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def allocate(self, base: str) -> str:
        count = self._counts.get(base, 0) + 1
        self._counts[base] = count
        return f"{base}_{count}" if count > 1 else base
