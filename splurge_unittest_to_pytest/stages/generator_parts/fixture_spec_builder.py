from dataclasses import dataclass

DOMAINS = ["generator", "fixtures"]


# Associated domains for this module


@dataclass
class FixtureSpec:
    name: str
    body: str


class FixtureSpecBuilder:
    """Create a minimal ``FixtureSpec`` used for scaffolding tests.

    The builder currently constructs a simple dataclass containing the
    fixture name and the source body string.
    """

    def build(self, name: str, body: str) -> FixtureSpec:
        return FixtureSpec(name=name, body=body)
