"""Type definitions for pipeline contexts and shared stage structures.

Small, stable TypedDicts and aliases used by pipeline stages. Introduced in
2025.2.0 as part of the Stage-1 refactor to make stage contexts explicit and
typed for future refactors.

Public:
    PipelineContext
"""

from __future__ import annotations

from typing import Any, TypedDict

DOMAINS = ["types", "pipeline"]


class PipelineContext(TypedDict, total=False):
    """TypedDict for passing state between stages in the conversion pipeline.

    Fields are intentionally permissive (total=False) to allow incremental
    migration; stages should document which keys they read/write.

    Common keys:
        module: libcst.Module - the current Module being transformed
        autocreate: bool - whether to autocreate tmp-backed fixtures
        pattern_config: Any - optional pattern configuration for method matching
        collector_output: Any - output produced by the Collector stage
    """

    module: Any
    autocreate: bool
    pattern_config: Any
    collector_output: Any
    # Common stage outputs
    needs_pytest_import: bool
    needs_re_import: bool
    needs_unittest_import: bool
    needs_sys_import: bool
    needs_os_import: bool
    needs_shutil_import: bool
    needs_typing_names: Any
    fixture_nodes: Any
    postvalidator_error: Any


__all__ = ["PipelineContext"]
