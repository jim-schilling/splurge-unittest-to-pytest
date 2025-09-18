"""Builder for simple fixture specifications used in tests.

This module exposes a dataclass ``FixtureSpec`` and a small builder
class used by generator tests to produce predictable fixture
descriptions.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from dataclasses import dataclass

DOMAINS = ["generator", "fixtures"]


# Associated domains for this module


@dataclass
class FixtureSpec:
    name: str
    body: str


class FixtureSpecBuilder:
    """Build a minimal FixtureSpec for tests.

    The builder constructs a simple dataclass holding the fixture name
    and the source body string. It is intentionally small to support
    deterministic unit tests.
    """

    def build(
        self,
        name: str,
        body: str,
    ) -> FixtureSpec:
        return FixtureSpec(name=name, body=body)
