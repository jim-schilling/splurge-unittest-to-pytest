"""Compact core that composes generator collaborators.

The ``GeneratorCore`` wires together small, testable components used by
the generator pipeline: name allocation, annotation inferer, fixture
builder, cleanup rewriter, and node emitter. It centralizes logic for
creating fixture nodes and finalizing generated results.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Any, Mapping

from .name_allocator import NameAllocator
from .annotation_inferer import AnnotationInferer, type_name_for_literal
from .literals import is_literal
from .fixture_spec_builder import FixtureSpecBuilder
from .cleanup_rewriter import CleanupRewriter
from .node_emitter import NodeEmitter
import libcst as cst

DOMAINS = ["generator"]


# Associated domains for this module


class GeneratorCore:
    """Core generator facade composed from small, testable parts.

    The core wires together collaborators (name allocator, inferer,
    builder, rewriter, and emitter) to provide a compact interface for
    creating fixture nodes and finalizing generated results.

    Public methods:
        make_fixture: Create a single fixture FunctionDef from a body
            string.
        make_composite_dirs_fixture: Create a grouped yield-style
            fixture that returns a dict of names to values.
        finalize: Annotate fixture nodes, collect typing requirements,
            and return the final result dict expected by the pipeline.
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

    def finalize(
        self,
        prepend_nodes: list[cst.BaseStatement],
        fixture_nodes: list[cst.FunctionDef],
        specs: Mapping[str, Any],
        bundler_typing: set[str] | None = None,
    ) -> dict[str, object]:
        """Annotate fixture nodes where possible, collect typing needs, and
        return the final result dict expected by the pipeline.

        This method mirrors the finalization logic previously in
        `stages/generator.py` and centralizes annotation/typing decisions so
        the generator can delegate to a small, testable core.
        """
        typing_needed: set[str] = set(bundler_typing or [])
        any_yield = False

        # Determine simple typing needs based on literal container shapes
        for spec in specs.values():
            v = getattr(spec, "value_expr", None)
            if isinstance(v, cst.List):
                typing_needed.add("List")
            elif isinstance(v, cst.Tuple):
                typing_needed.add("Tuple")
            elif isinstance(v, cst.Set):
                typing_needed.add("Set")
            elif isinstance(v, cst.Dict):
                typing_needed.add("Dict")
            else:
                if v is not None and not is_literal(v):
                    typing_needed.add("Any")
            if getattr(spec, "yield_style", False):
                any_yield = True

        if any_yield:
            typing_needed.add("Generator")

        # Attach return annotations to generated fixture functions when we
        # can infer a specific typing annotation and the fixture accepts no
        # parameters.
        annotated_nodes: list[cst.BaseStatement] = []
        for n in fixture_nodes:
            if isinstance(n, cst.FunctionDef):
                nm = n.name.value
                spec_opt = specs.get(nm)
                if spec_opt is not None and getattr(spec_opt, "value_expr", None) is not None:
                    if not n.params.params:
                        ann_node, extra_names = type_name_for_literal(spec_opt.value_expr)
                        if ann_node is not None:
                            annotated = n.with_changes(returns=cst.Annotation(annotation=ann_node))
                            annotated_nodes.append(annotated)
                            typing_needed.update(extra_names)
                            continue
            annotated_nodes.append(n)

        final_nodes = list(prepend_nodes) + annotated_nodes

        result: dict[str, object] = {"fixture_specs": specs, "fixture_nodes": final_nodes}
        if typing_needed:
            result["needs_typing_names"] = sorted(typing_needed)
        needs_shutil = any(getattr(s, "_needs_shutil", False) for s in specs.values())
        if needs_shutil:
            result["needs_shutil_import"] = True
        return result
