# Plan: Make `migrate` a thin wrapper and add `main.migrate()` API

Goal

- Make the current CLI command `migrate` a thin wrapper that delegates to a new module-level API function `main.migrate()` so migrations can be invoked both from the CLI and programmatically via an import.

Motivation

- Improves testability and reusability: callers can import and invoke `main.migrate()` directly from other Python code (CI scripts, tools, or unit tests).
- Keeps the CLI surface small and focused on argument parsing and validation.
- Makes it easier to write automated integration tests for migration behavior without invoking the CLI runner.

Scope

- Add a new module `splurge_unittest_to_pytest.main` with a public function `migrate(source_files, *, config: MigrationConfig | None = None) -> Result`.
- Update `splurge_unittest_to_pytest.cli:migrate` to parse CLI args, create `MigrationConfig`, then call `main.migrate(...)` and handle return codes and logging.
- Ensure `main.migrate` is safe to call both with a `MigrationConfig` object and with CLI-style parameters.
- Update tests and add focused unit tests for the wrapper behavior.

High-level tasks

1. Add `splurge_unittest_to_pytest/main.py` exposing `migrate()`
   - Signature: `def migrate(source_files: list[str], config: MigrationConfig | None = None) -> Result[list[str]]`
   - Responsibilities: validate inputs (re-use helpers in `cli.py` if desirable), instantiate `MigrationOrchestrator`, call orchestrator.migrate_file or migrate_directory as appropriate, return `Result` objects.
   - Should not call `typer` or do CLI parsing; it should be pure API.

2. Update `cli.py:migrate` to be a thin wrapper
   - Keep argument parsing and `typer`-specific behavior here.
   - Create `MigrationConfig` via `create_config(...)` and then call `main.migrate(source_files, config=config)`.
   - Map the `Result` to proper exit codes and print/log as before.

3. Wire parametrize flag through the pipeline (follow-up PR)
   - Ensure code paths that instantiate `UnittestToPytestTransformer` pass `parametrize=config.parametrize` when the pipeline builds transformers (MigrationOrchestrator/PipelineFactory). This keeps the runtime behavior consistent with CLI flags.

4. Tests
   - Add unit tests for `main.migrate` that call it programmatically with a temporary test file and verify the `Result` and output file content.
   - Add a small test asserting `cli.migrate` calls `main.migrate` and handles a successful and failing Result correctly (use monkeypatching or a small integration test folder).

Acceptance criteria

- `splurge_unittest_to_pytest.main.migrate` exists and is importable.
- `cli.migrate` delegates to `main.migrate` for the heavy lifting and returns CLI-appropriate exit codes.
- Unit tests exist for core paths (success/failure) and pass locally.
- No change in current default behavior (CLI still functions the same), except that behavior is now implemented in `main.migrate()`.

Risks & mitigations

- Risk: accidental duplication of validation code between `cli` and `main`. Mitigation: keep validation helpers in `cli` or a small `utils` helper and reuse them.
- Risk: breaking backward compatibility for existing callers that import CLI. Mitigation: keep `cli` function signature stable and only change internals.

Estimated work & timeline

- Create `main.py` and wire `cli.py` (1-2 hours)
- Add unit tests + CI run (1-2 hours)
- Optional: wire config.parametrize through pipeline (follow-up, 1-2 hours)


---

Created by automated plan generator. Edit this file to add more implementation details or split into smaller tasks if desired.
