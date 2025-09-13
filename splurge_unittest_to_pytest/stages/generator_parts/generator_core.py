from .name_allocator import NameAllocator
from .annotation_inferer import AnnotationInferer
from .fixture_spec_builder import FixtureSpecBuilder
from .cleanup_rewriter import CleanupRewriter
from .node_emitter import NodeEmitter


class GeneratorCore:
    """Compose small components to provide a simple generator facade."""

    def __init__(self) -> None:
        self.names = NameAllocator()
        self.inferer = AnnotationInferer()
        self.builder = FixtureSpecBuilder()
        self.rewriter = CleanupRewriter()
        self.emitter = NodeEmitter()

    def make_fixture(self, base_name: str, body: str) -> str:
        name = self.names.allocate(base_name)
        cleaned = self.rewriter.rewrite(body)
        spec = self.builder.build(name=name, body=cleaned)
        return self.emitter.emit_fixture(spec.name, spec.body)
