Rewrite invariants and parser shapes
=====================================

Date: 2025-09-28

Purpose
-------

Brief developer note describing the invariants we follow when rewriting
assertions that reference an alias-bound log-like object (for example
``log.output``) to pytest ``caplog`` equivalents.

Invariants
----------

- Conservative rewrites only: if we cannot conclusively identify or
  safely transform a node, we return ``None`` and leave the original
  code unchanged.
- Only rewrite expressions that reference the provided alias name when
  the shape is recognized (``Comparison``, membership ``In``, ``len``
  checks, equality comparisons, etc.).
- Walk into and rewrite the following CST shapes where appropriate:
  - ``ParenthesizedExpression`` wrapping a ``Comparison``
  - ``UnaryOperation`` (``not``) whose ``expression`` is one of the
    handled shapes
  - ``BooleanOperation`` combining comparisons (``and``/``or``)
- When rewriting membership checks (``'err' in log.output[0]``) we map
  the sequence of attribute/subscript accesses to ``caplog.records[...]``
  and call ``.getMessage()`` on the resulting record expression.

Why these invariants?
---------------------
They keep automated transformations safe across a wide range of input
styles while minimizing false-positives. The parser/AST can represent
semantically-equivalent source using different CST shapes; the policy
above ensures we only transform when the mapping to ``caplog`` is
unambiguous.

Notes for future contributors
-----------------------------
- Prefer adding small, focused unit tests for any new rewrite shape.
- If you consider adding a more aggressive best-effort rewrite, add a
  flag or explicit opt-in so transformations remain auditable.

