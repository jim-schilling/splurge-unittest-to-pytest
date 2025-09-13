class NodeEmitter:
    """Scaffold node emitter that converts fixture specs to source text."""

    def emit_fixture(self, name: str, body: str) -> str:
        # detect simple yield-style bodies and add @pytest.fixture decorator
        if "yield" in body or "try:" in body:
            return f"@pytest.fixture\ndef {name}():\n{body}\n"
        return f"def {name}():\n{body}\n"
