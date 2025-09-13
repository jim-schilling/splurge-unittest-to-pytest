from .name_allocator import NameAllocator
from .annotation_inferer import AnnotationInferer
from .fixture_spec_builder import FixtureSpecBuilder
from .cleanup_rewriter import CleanupRewriter
from .node_emitter import NodeEmitter
import libcst as cst


class GeneratorCore:
    """Compose small components to provide a simple generator facade."""

    def __init__(self) -> None:
        self.names = NameAllocator()
        self.inferer = AnnotationInferer()
        self.builder = FixtureSpecBuilder()
        self.rewriter = CleanupRewriter()
        self.emitter = NodeEmitter()

    def make_fixture(self, base_name: str, body: str) -> cst.FunctionDef:
        name = self.names.allocate(base_name)
        cleaned = self.rewriter.rewrite(body)
        spec = self.builder.build(name=name, body=cleaned)
        # emit a libcst node for the fixture
        return self.emitter.emit_fixture_node(spec.name, spec.body)

    def make_composite_dirs_fixture(self, base_name: str, mapping: dict[str, str]) -> cst.FunctionDef:
        """Create a grouped yield-style fixture that returns a dict of names->values.

        mapping: attribute name -> body expression (string)
        """
        # build body lines: create local vars then yield a dict, then cleanup
        body_lines: list[str] = []
        for k, expr in mapping.items():
            body_lines.append(f"    {k} = {expr}")
        # build yield dict line
        entries = ", ".join([f'"{k}": {k}' for k in mapping.keys()])
        body_lines.append("    try:")
        body_lines.append(f"        yield {{{entries}}}")
        body_lines.append("    finally:")
        for k in mapping.keys():
            body_lines.append("        pass")
        body_src = "\n".join(body_lines)
        # prefer emitting a proper composite dirs node when available
        try:
            return self.emitter.emit_composite_dirs_node(base_name, mapping)
        except Exception:
            return self.emitter.emit_fixture_node(base_name, body_src)
