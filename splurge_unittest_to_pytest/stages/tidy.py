"""Final tidy stage: spacing normalization and light post-processing.

Performs the centralized formatting pass using :func:`normalize_module`
and enforces canonical blank-line counts and class-method parameter
expectations. This is the last stage in the pipeline and prepares the
module for output.

Publics:
    tidy_stage

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Optional, cast
from ..types import PipelineContext

import libcst as cst

from splurge_unittest_to_pytest.stages.formatting import normalize_module

DOMAINS = ["stages", "tidy"]

# Associated domains for this module


def tidy_stage(context: PipelineContext) -> PipelineContext:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    if module is None:
        return {"module": module}

    # Centralized formatting pass
    normalized = normalize_module(module)

    # Final pass: ensure exactly two EmptyLine nodes before each top-level
    # FunctionDef or ClassDef. This enforces canonical spacing regardless of
    # what earlier stages inserted or omitted.
    final_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
    for node in list(normalized.body):
        if isinstance(node, (cst.FunctionDef, cst.ClassDef)):
            # remove trailing EmptyLine nodes from final_body to avoid churn
            while final_body and isinstance(final_body[-1], cst.EmptyLine):
                final_body.pop()
            final_body.append(cast(cst.BaseSmallStatement, cst.EmptyLine()))
            final_body.append(cast(cst.BaseSmallStatement, cst.EmptyLine()))
            final_body.append(node)
            continue
        final_body.append(node)

    normalized = normalized.with_changes(body=final_body)

    # Ensure class test methods have a 'self' parameter when missing
    class EnsureSelfParam(cst.CSTTransformer):
        def __init__(self) -> None:
            super().__init__()
            self._in_class = False

        def visit_ClassDef(self, node: cst.ClassDef) -> None:
            self._in_class = True

        def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
            self._in_class = False
            return updated_node

        def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
            if not self._in_class:
                return updated_node
            if not original_node.name.value.startswith("test"):
                return updated_node
            if not updated_node.params.params:
                new_params = [cst.Param(name=cst.Name("self"))]
                return updated_node.with_changes(params=updated_node.params.with_changes(params=new_params))
            return updated_node

    final_module = normalized.visit(EnsureSelfParam())
    return {"module": final_module}
