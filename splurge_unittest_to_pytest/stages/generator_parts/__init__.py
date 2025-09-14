"""Generator stage helper components.

This package contains small, well-defined components used by the
generator stage. Stage 1 scaffolds minimal implementations so we can
incrementally refactor with tests.
"""

from .name_allocator import NameAllocator
from .annotation_inferer import AnnotationInferer
from .fixture_spec_builder import FixtureSpecBuilder
from .cleanup_rewriter import CleanupRewriter
from .node_emitter import NodeEmitter
from .generator_core import GeneratorCore

__all__ = [
    "NameAllocator",
    "AnnotationInferer",
    "FixtureSpecBuilder",
    "CleanupRewriter",
    "NodeEmitter",
    "GeneratorCore",
]
