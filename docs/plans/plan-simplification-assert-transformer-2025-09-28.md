# Plan: Simplify `wrap_assert_in_block` (2025-09-28)

Goal: Decompose `wrap_assert_in_block()` in `splurge_unittest_to_pytest/transformers/assert_transformer.py` into smaller single-responsibility functions, implement the refactor incrementally, and keep behavior identical (conservative fallbacks on errors).

Checklist (implementation in small, verifiable steps):

- [x] Read and analyze `wrap_assert_in_block` and identify responsibilities (done).

- [x] Draft decomposition and helper function list (high-level plan):
  - `get_self_attr_call(stmt)`: detect bare `self`/`cls` attribute call statements.
  - `build_with_item_from_assert_call(call_expr)`: build `WithItem` (pytest.warns/raises/caplog.at_level) from `self.assert*` call.
  - `create_with_wrapping_next_stmt(with_item, next_stmt)`: produce a `With` node wrapping next statement or `pass`.
  - `transform_standalone_assert_calls(statements)`: scan and replace standalone assert calls with With blocks.
  - `transform_with_items(stmt)`: rewrite items inside existing `With`s to pytest equivalents and detect alias names.
  - `rewrite_asserts_using_alias_in_with_body(with_node, alias_name)`: rewrite asserts inside a With body referencing an alias to `caplog.records` / `.getMessage()`.
  - `rewrite_following_statements_for_alias(statements, alias_name, start_index, look_ahead)`: look-ahead rewrites after a With.
  - `rewrite_assert_stmt_for_alias(node, alias_name)`: helper to rewrite a single statement referencing alias.

- [x] Create plan doc (this file).

- [x] Start implementing (small, safe first step):
  - [x] Add `get_self_attr_call` and `build_with_item_from_assert_call` helpers above `wrap_assert_in_block`.
  - [ ] Add tests for these helpers (unit tests).

Detailed helper list and associated tests
---------------------------------------

The following helpers will be implemented one-by-one. For each helper I list:
- signature (pythonic)
- responsibility
- inputs/outputs
- key edge cases and invariants
- the unit tests to add (file + test behavior)

1) _get_self_attr_call(stmt: cst.BaseStatement) -> tuple[str, cst.Call] | None
   - Responsibility: Detect a bare expression statement that is a `self`/`cls` attribute call (e.g., `self.assertLogs(...)`) and return the attribute name and the call node.
   - Inputs/Outputs: Input is any `cst.BaseStatement`. Output is (attr_name, Call) or None.
   - Edge cases: Only accept `SimpleStatementLine` with exactly one `Expr`; ignore other shapes. Only match when the attribute base is `self` or `cls`.
   - Tests (unit): `tests/unit/test_assert_transformer_helpers.py`
     - test_get_self_attr_call_matches_self_expr: parse `self.assertLogs('x')` as statement and assert returns ("assertLogs", Call).
     - test_get_self_attr_call_none_for_non_expr: pass an `Assign` or other statement and assert None.

2) _build_with_item_from_assert_call(call_expr: cst.Call) -> cst.WithItem | None
   - Responsibility: Given a Call whose func is `self`/`cls` attribute, produce the correct `WithItem` for known context-asserts: `assertWarns`, `assertWarnsRegex`, `assertRaises`, `assertRaisesRegex`, `assertLogs`, `assertNoLogs`.
   - Inputs/Outputs: Input: `cst.Call` node. Output: `cst.WithItem` or None.
   - Edge cases: map keyword `match=` for regex/warns, use default caplog level of "INFO" when level missing, avoid preserving `as` alias for caplog conversion (tests depend on using `caplog` fixture), preserve `pytest.raises` signature arguments (as in original file).
   - Tests (unit): `tests/unit/test_assert_transformer_helpers.py`
     - test_build_with_item_warns_and_match: call_expr for `self.assertWarns(Exception, match='x')` yields WithItem wrapping `pytest.warns(Exception, match='x')`.
     - test_build_with_item_assertlogs_default_level: `self.assertLogs('logger')` yields `caplog.at_level("INFO")` WithItem.
     - test_build_with_item_raises: `self.assertRaises(MyErr)` yields `pytest.raises(MyErr)` WithItem.

3) _create_with_wrapping_next_stmt(with_item: cst.WithItem, next_stmt: cst.BaseStatement | None) -> cst.With
   - Responsibility: Given a WithItem and an optional next statement, produce a `cst.With` whose body is either the next statement (unwrapping inner With bodies if next_stmt is itself a With) or a `pass` body when next_stmt is None.
   - Inputs/Outputs: WithItem and optional statement -> With node.
   - Edge cases: If next_stmt is a `With`, use its inner `body` rather than nesting With -> keep same `IndentedBlock` shape.
   - Tests (unit): `tests/unit/test_assert_transformer_with_creation.py`
     - test_create_with_wraps_statement: ensure `with caplog.at_level(...): <stmt>` produced.
     - test_create_with_unwraps_inner_with: next_stmt is a With with body -> resulting With should contain inner body.
     - test_create_with_pass_when_none: next_stmt None -> body contains `pass`.

4) transform_standalone_assert_calls(statements: list[cst.BaseStatement]) -> list[cst.BaseStatement]
   - Responsibility: Full pass over statement list, detecting bare `self`/`cls` assert-calls and replacing them with `With` nodes that wrap the following statement or pass. This is a small orchestrating helper that uses the three helpers above.
   - Inputs/Outputs: List of statements -> new list of statements (same length or shorter if wrapping consumes following statement).
   - Edge cases: preserve index stepping (advance by 2 when wrapping); preserve unaffected statements; keep conservative behavior if helper returns None.
   - Tests (integration/unit): `tests/unit/test_assert_transformer_wrap_and_alias.py` (existing) and new tests in `tests/unit/test_assert_transformer_wrap_creation.py`
     - test_wrap_assert_logs_followed_by_stmt: input lines [self.assertLogs(...), assert len(log.output) == 2] -> With wrapping and body containing len rewrite later stages.
     - test_wrap_assert_no_following_stmt: single `self.assertLogs(...)` -> With with pass body.

5) transform_with_items(stmt: cst.With) -> tuple[cst.With, str | None, bool]
   - Responsibility: Given a `With` node, rewrite items that are `self`/`cls` attribute calls into pytest equivalents (warns, raises, caplog.at_level). Return the new With, detected alias name if any (original `as X`), and a `changed` flag.
   - Inputs/Outputs: `cst.With` -> (new `cst.With`, alias_name or None, changed flag)
   - Edge cases/invariants: preserve `asname` for `raises` (original code preserved item.asname for raises); do not preserve alias for caplog conversions (tests expect caplog fixture). Keep try/except fallback around whole transformation.
   - Tests (unit): `tests/unit/test_assert_transformer_with_items.py`
     - test_transform_with_items_assertlogs_as_alias: `with self.assertLogs(...) as log:` -> With containing `caplog.at_level(...)` without `as` alias and returns alias_name == 'log'.
     - test_transform_with_items_raises_preserve_as: `with self.assertRaises(E) as cm:` -> new WithItem with `pytest.raises(E)` and `asname` preserved.

6) rewrite_asserts_using_alias_in_with_body(with_node: cst.With, alias_name: str) -> cst.With
   - Responsibility: Given a With whose original WithItem had an alias name, rewrite `Assert` statements and `SimpleStatementLine`-wrapped asserts inside the With body to reference `caplog.records` instead of `alias.output`, and to insert `.getMessage()` on records when required (membership/equality patterns).
   - Inputs/Outputs: `cst.With`, alias_name -> rewritten `cst.With` (or original on failure)
   - Edge cases: handle both `Assert` and `SimpleStatementLine` wrapper cases; support `Subscript` (alias.output[0]) and plain attribute (alias.output); avoid altering unrelated expressions; preserve wrapper vs bare assert statement shapes.
   - Tests (unit): `tests/unit/test_assert_transformer_alias_body_rewrites.py`
     - test_rewrite_len_alias_output: inside With body `assert len(log.output) == 2` -> `assert len(caplog.records) == 2`.
     - test_rewrite_membership_alias_output_subscript: `assert 'msg' in log.output[0]` -> `assert 'msg' in caplog.records[0].getMessage()`.
     - test_rewrite_equality_alias_output: `assert caplog.records[0] == 'msg'` -> `assert caplog.records[0].getMessage() == 'msg'`.

7) rewrite_following_statements_for_alias(statements: list[cst.BaseStatement], alias_name: str, start_index: int, look_ahead: int = 12) -> None
   - Responsibility: After transforming a With that had an alias, look ahead up to `look_ahead` statements and rewrite patterns referencing the alias into caplog variants (same logic as `rewrite_asserts_using_alias_in_with_body` but on later statements). This keeps parity with existing look-ahead behavior.
   - Inputs/Outputs: modifies `statements` in-place.
   - Edge cases: bounds-checking, stop early when no matches; keep same look-ahead limit default 12.
   - Tests (unit): `tests/unit/test_assert_transformer_alias_lookahead.py` (existing) plus:
     - test_lookahead_rewrites_len_and_membership: after a With with `as log`, assert statements 3 lines later referencing `log.output` are rewritten.

8) rewrite_assert_stmt_for_alias(node: cst.BaseStatement, alias_name: str) -> cst.BaseStatement | None
   - Responsibility: Helper that rewrites a *single* statement (Assert or SimpleStatementLine wrapping an Assert or self.assert* call) if it references the alias, returning the rewritten statement or None.
   - Tests (unit): covered by tests for (6) and (7). Add specific tests for Single-statement transforms.

9) small internal helpers: _rewrite_eq_node(node: cst.CSTNode, alias_name: str) -> cst.CSTNode | None
   - Responsibility: Shared logic used by alias-rewrite helpers that maps attribute/subscript forms referencing `alias.output` to caplog equivalents and optionally `getMessage()` wrappers for equality membership contexts.
   - Tests (unit): small targeted tests used by other unit tests.

Integration tests (end-to-end)
--------------------------------
- Existing tests in `tests/unit/test_assert_transformer_*` already cover many scenarios; we will add/adjust tests as we extract helpers to assert behavior remains unchanged.
- Add two integration tests to ensure the full `wrap_assert_in_block` behavior remains identical after refactor:
  - `tests/integration/test_assert_logs_wrap_and_alias_rewrite.py`:
    - sample input with `self.assertLogs(...)
      with ... as log:` and following statements that reference `log.output`. Verify the resulting AST/code matches expected output using the existing transformer pipeline.
  - `tests/integration/test_assert_raises_and_warns_with_items.py`:
    - input with `with self.assertRaises(E) as cm:` and `with self.assertWarns(Warn):` forms to verify proper pytest conversions and alias preservation semantics.

Order of implementation (incremental, each followed by tests):
1. Implement `_get_self_attr_call` and `_build_with_item_from_assert_call` (done).
2. Implement `_create_with_wrapping_next_stmt` and refactor top-level bare-expression branch to call it (small change).
3. Add unit tests for helpers in step 1 & 2 and run test subset.
4. Extract `transform_with_items` from `elif isinstance(stmt, cst.With):` block. Add tests for `assertLogs`/`assertRaises` conversions and alias detection.
5. Extract `rewrite_asserts_using_alias_in_with_body` and `rewrite_assert_stmt_for_alias` and unit tests for alias rewrites.
6. Extract `rewrite_following_statements_for_alias` and confirm look-ahead tests pass.
7. Replace in-place logic in `wrap_assert_in_block` by orchestrating calls to these helpers; run full test suite.

Acceptance criteria
- Each helper has at least one focused unit test covering the happy path and one edge-case.
- After each extraction step, run the test suite and ensure no regressions.
- Preserve existing conservative try/except fallback behavior where present.

If you approve this detailed plan, I'll proceed to implement step 2 (`_create_with_wrapping_next_stmt` and refactor the bare-expression branch to use it), add the helper unit tests, and run the tests. Otherwise tell me which helper to implement next.

- [ ] Replace the inline logic for handling bare expression `self.assert*` calls in `wrap_assert_in_block` with calls to the new helpers.
  - [ ] Run unit tests; fix any regressions.

- [ ] Extract `transform_with_items` and related alias-body rewrite logic into helpers, preserving exception-safety.
  - [ ] Add tests for With-item rewriting and alias rewriting.

- [ ] Replace the in-place look-ahead rewrite code with `rewrite_following_statements_for_alias` and verify behavior with tests.

- [ ] Run full test suite and linters (ruff/mypy) and fix issues.

- [ ] Final tidy: docstrings, type annotations, small refactor commit messages, open PR on `chore/simplificaton` branch.

Notes / Acceptance criteria:
- Preserve current runtime behavior for supported patterns (standalone assert calls, With-item conversion, alias rewrite patterns).
- Keep conservative try/except fallbacks where the original code did so.
- Maintain existing test expectations (caplog alias removal, `pytest.raises` alias preservation, default caplog level fallback to "INFO").

If you'd like, I'll continue and extract the next logical chunk: replace the `bare expression` handling in `wrap_assert_in_block` to call these new helpers and add unit tests. Otherwise I can stop here and await guidance.
