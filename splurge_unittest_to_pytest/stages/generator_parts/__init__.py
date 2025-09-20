"""Generator stage helper components.

This package exposes small, focused components used by the generator
stage. The implementations are minimal scaffolds to support incremental
refactoring and deterministic unit tests.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from .annotation_inferer import AnnotationInferer
from .cleanup_rewriter import CleanupRewriter
from .fixture_spec_builder import FixtureSpecBuilder
from .generator_core import GeneratorCore
from .name_allocator import NameAllocator
from .node_emitter import NodeEmitter

__all__ = [
    "NameAllocator",
    "AnnotationInferer",
    "FixtureSpecBuilder",
    "CleanupRewriter",
    "NodeEmitter",
    "GeneratorCore",
]
