Developer note: caplog mapping policy (no synthetic alias)

Summary
-------
This project normalizes unittest `assertLogs` and `caplog` usages to a consistent pytest caplog pattern. The transformation rules are implemented in:

- `splurge_unittest_to_pytest/transformers/assert_transformer.py` (libcst-level rewrites)
- A conservative string-level fallback in the same module handles edge-case textual patterns the AST pass may miss.

Policy and behavior
-------------------
1. The transformer MUST NOT introduce a synthetic private alias such as `as _caplog`. All transformed code should reference the pytest `caplog` fixture directly. Example:

- Original: `with caplog.at_level("INFO"):`
- Converted: `with caplog.at_level("INFO"):`

2. Message access semantics are expressed via `caplog.messages` (a list-like view of captured messages). The string-level fallback rewrites uses of `caplog.records` and `<alias>.output` to `caplog.messages` when necessary.

Why this policy?
-----------------
- Avoids leaking synthetic identifiers into the user's code and removes another source of surprise or collision with existing names.
- Produces simpler, easier-to-read transformed code that relies on pytest's documented `caplog` fixture surface.

Tests & expectations
--------------------
- Unit and integration tests should NOT expect `as _caplog` anywhere in transformed output.
- Tests should assert that the transformer injects the `caplog` fixture when necessary and that message access uses `caplog.messages`.

Suggested follow-ups
--------------------
- Add a small guard unit test that fails if any transform output contains the substring `as _caplog`.
- Keep this document updated whenever `assert_transformer.py` or the string fallback changes.
