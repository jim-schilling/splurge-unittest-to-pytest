from dataclasses import dataclass


@dataclass
class FixtureSpec:
    name: str
    body: str


class FixtureSpecBuilder:
    """Create a minimal FixtureSpec for scaffolding tests."""

    def build(self, name: str, body: str) -> FixtureSpec:
        return FixtureSpec(name=name, body=body)
