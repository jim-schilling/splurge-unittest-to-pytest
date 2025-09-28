"""Helpers for recording and applying AST replacements across passes.

This module provides two small utilities used by multi-pass libcst
transformations:

- :class:`ReplacementRegistry` records planned node replacements keyed
    by source position metadata so nodes can be matched across passes.
- :class:`ReplacementApplier` is a :class:`libcst.CSTTransformer` that
    applies the recorded replacements during a second-pass traversal. It
    depends on :class:`libcst.metadata.PositionProvider` metadata.

These helpers are useful when a transformation pass needs to record
that a later pass should replace a specific expression or statement,
and object identity cannot be relied upon between passes.
"""

from __future__ import annotations

import libcst as cst
from libcst.metadata import PositionProvider


class ReplacementRegistry:
    """Registry for planned libcst node replacements keyed by source position.

    The registry stores replacements using a position key derived from
    :class:`libcst.metadata.PositionProvider` metadata: a
    ``(start_line, start_col, end_line, end_col)`` tuple. Storing by
    position rather than object identity allows matching nodes between
    separate transformation passes where node objects may have changed.

    Typical usage:
        registry = ReplacementRegistry()
        registry.record(pos, new_node)
        applier = ReplacementApplier(registry)

    Note:
        The :meth:`key_from_position` helper expects a metadata ``pos``
        object with ``start``/``end`` attributes as provided by
        ``PositionProvider``.
    """

    def __init__(self) -> None:
        # map from position tuple to replacement node
        self.replacements: dict[tuple[int, int, int, int], cst.CSTNode] = {}

    @staticmethod
    def key_from_position(pos) -> tuple[int, int, int, int]:
        """Return a 4-tuple key for the given position metadata object.

        Args:
            pos: A PositionProvider metadata object exposing ``start`` and
                ``end`` attributes with ``line`` and ``column`` fields.

        Returns:
            A tuple ``(start_line, start_col, end_line, end_col)`` used
            as the registry key.
        """

        return (pos.start.line, pos.start.column, pos.end.line, pos.end.column)

    def record(self, pos, new_node: cst.CSTNode) -> None:
        key = self.key_from_position(pos)
        self.replacements[key] = new_node

    def get(self, pos) -> cst.CSTNode | None:
        """Return a recorded replacement node for the given position.

        Args:
            pos: A PositionProvider metadata object.

        Returns:
            A :class:`libcst.CSTNode` previously recorded for that
            position, or ``None`` if no replacement was recorded.
        """

        return self.replacements.get(self.key_from_position(pos))


class ReplacementApplier(cst.CSTTransformer):
    """CSTTransformer that applies replacements recorded in a registry.

    This transformer expects the ``PositionProvider`` metadata to be
    available on the module. For each visited node it checks whether a
    replacement was recorded in the supplied :class:`ReplacementRegistry`
    and substitutes the recorded node when appropriate.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, registry: ReplacementRegistry) -> None:
        super().__init__()
        self.registry = registry

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        # If an expression-level replacement exists for this call, apply it.
        try:
            pos = self.get_metadata(PositionProvider, original_node)
            repl = self.registry.get(pos)
            if repl is not None and isinstance(repl, cst.BaseExpression):
                return repl  # replace the call expression
        except Exception:
            pass
        return updated_node

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.BaseStatement:
        # If the simple statement is a single Expr(Call(...)) and the recorded
        # replacement for that Call is a statement (e.g., Assert), substitute it.
        try:
            if len(original_node.body) == 1 and isinstance(original_node.body[0], cst.Expr):
                expr = original_node.body[0].value
                if isinstance(expr, cst.Call):
                    pos = self.get_metadata(PositionProvider, expr)
                    repl = self.registry.get(pos)
                    if repl is not None and isinstance(repl, cst.BaseStatement):
                        return repl
        except Exception:
            pass
        return updated_node
