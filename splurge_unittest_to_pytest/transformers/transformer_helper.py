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

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from __future__ import annotations

import logging

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
        self._logger = logging.getLogger(__name__)

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        # If an expression-level replacement exists for this call, apply it.
        try:
            pos = self.get_metadata(PositionProvider, original_node)
            repl = self.registry.get(pos)
            if repl is not None and isinstance(repl, cst.BaseExpression):
                try:
                    pos = self.get_metadata(PositionProvider, original_node)
                    key = self.registry.key_from_position(pos)
                except Exception:
                    key = None
                self._logger.debug("ReplacementApplier: replacing Call at %s with %s", key, type(repl).__name__)
                return repl  # replace the call expression
        except (AttributeError, TypeError, IndexError):
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
                        # Ensure the replacement is a SimpleStatementLine when
                        # inserted into an IndentedBlock body. Some transforms
                        # return small-statement nodes (for example cst.Assert)
                        # which must be wrapped in a SimpleStatementLine to
                        # preserve correct indentation/formatting when rendered.
                        try:
                            # Copy leading_lines metadata from the original
                            leading = getattr(original_node, "leading_lines", ())
                        except Exception:
                            leading = ()

                        try:
                            pos = self.get_metadata(PositionProvider, expr)
                            key = self.registry.key_from_position(pos)
                        except Exception:
                            key = None
                        self._logger.debug(
                            "ReplacementApplier: found statement-level replacement at %s -> %s",
                            key,
                            type(repl).__name__,
                        )

                        # If the replacement is already a SimpleStatementLine,
                        # preserve it and copy metadata when possible.
                        if isinstance(repl, cst.SimpleStatementLine):
                            try:
                                # Always return the recorded SimpleStatementLine.
                                # If there are leading_lines on the original node,
                                # copy them onto the replacement when possible so
                                # formatting is preserved. If not, return the
                                # replacement as-is.
                                if hasattr(repl, "with_changes") and leading:
                                    self._logger.debug(
                                        "ReplacementApplier: preserving leading_lines on existing SimpleStatementLine at %s",
                                        key,
                                    )
                                    return repl.with_changes(leading_lines=leading)
                                self._logger.debug(
                                    "ReplacementApplier: returning existing SimpleStatementLine at %s",
                                    key,
                                )
                                return repl
                            except Exception:
                                return repl

                        # Otherwise wrap the replacement into a SimpleStatementLine
                        try:
                            # Only wrap when the replacement is a BaseSmallStatement
                            # (for example an Assert or Pass). Wrapping compound
                            # statements (Try/With/If) into a SimpleStatementLine
                            # is invalid. If the replacement is not a
                            # BaseSmallStatement, return it directly.
                            if isinstance(repl, cst.BaseSmallStatement):
                                wrapped = cst.SimpleStatementLine(body=[repl])
                                if leading and hasattr(wrapped, "with_changes"):
                                    wrapped = wrapped.with_changes(leading_lines=leading)
                                self._logger.debug(
                                    "ReplacementApplier: wrapped %s into SimpleStatementLine at %s",
                                    type(repl).__name__,
                                    key,
                                )
                                return wrapped
                            # Not a small-statement: return the replacement as-is
                            self._logger.debug(
                                "ReplacementApplier: replacement %s is not a small-statement, returning as-is",
                                type(repl).__name__,
                            )
                            return repl
                        except Exception:
                            # If wrapping fails, return the raw replacement
                            self._logger.exception("ReplacementApplier: failed to wrap replacement at %s", key)
                            return repl
        except (AttributeError, TypeError, IndexError):
            pass
        return updated_node
