from dataclasses import dataclass

DOMAINS = ["generator", "fixtures"]


# Associated domains for this module


@dataclass
class FixtureSpec:
    name: str
    body: str


class FixtureSpecBuilder:
    """Create a minimal FixtureSpec for scaffolding tests."""

    def build(self, name: str, body: str) -> FixtureSpec:
        return FixtureSpec(name=name, body=body)
