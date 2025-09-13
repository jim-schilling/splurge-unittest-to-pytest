class NodeEmitter:
    """Scaffold node emitter that converts fixture specs to source text."""

    def emit_fixture(self, name: str, body: str) -> str:
        return f"def {name}():\n{body}\n"
