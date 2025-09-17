"""Generator stage helper components.

This package exposes small, focused components used by the generator
stage. The implementations are minimal scaffolds to support incremental
refactoring and deterministic unit tests.
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
