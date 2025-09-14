from .name_allocator import NameAllocator
from .annotation_inferer import AnnotationInferer
from .fixture_spec_builder import FixtureSpecBuilder
from .cleanup_rewriter import CleanupRewriter
from .node_emitter import NodeEmitter
import libcst as cst


class GeneratorCore:
    """Compose small components to provide a simple generator facade.

    The core can accept injected collaborators to make unit-testing and
    orchestration testing straightforward.
    """

    def __init__(
        self,
        names: NameAllocator | None = None,
        inferer: AnnotationInferer | None = None,
        builder: FixtureSpecBuilder | None = None,
        rewriter: CleanupRewriter | None = None,
        emitter: NodeEmitter | None = None,
    ) -> None:
        self.names = names or NameAllocator()
        self.inferer = inferer or AnnotationInferer()
        self.builder = builder or FixtureSpecBuilder()
        self.rewriter = rewriter or CleanupRewriter()
        self.emitter = emitter or NodeEmitter()

    def make_fixture(self, base_name: str, body: str) -> cst.FunctionDef:
        name = self.names.allocate(base_name)
        cleaned = self.rewriter.rewrite(body)
        spec = self.builder.build(name=name, body=cleaned)
        # emit a libcst node for the fixture
        # Ask the inferer whether we should add a return annotation. The
        # inferer returns a string like '-> Any' or '-> None'. Normalize
        # and pass the short token (e.g. 'Any') to the emitter when present.
        try:
            ann = self.inferer.infer_return_annotation(spec.name)
        except Exception:
            ann = None

        returns_token = None
        if isinstance(ann, str) and ann.startswith("->"):
            token = ann[2:].strip()
            if token and token != "None":
                returns_token = token

        return self.emitter.emit_fixture_node(spec.name, spec.body, returns=returns_token)

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
