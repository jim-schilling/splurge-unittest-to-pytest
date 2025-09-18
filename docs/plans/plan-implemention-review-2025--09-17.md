```markdown
Title: splurge-unittest-to-pytest — implementation checklist for review (2025-09-17)

Purpose
- Turn the "Staged action plan" from `plan-review-2025-09-17.md` into a prescriptive, checklist-style implementation plan. Each stage lists concrete tasks, suggested files to edit, test/acceptance criteria, and low-risk sequencing notes.

Notes and assumptions
- This plan assumes the repository layout and filenames described in the review (e.g., `cli.py`, `main.py`, `stages/`, `converter/`).
- Where a new helper file is recommended (for atomic writes or encoding detection), suggest `splurge_unittest_to_pytest/io_helpers.py` or similar.
- Owners are optional: put initials or leave blank when unknown.

Checklist (staged)

- Stage-1: Policy and simplification (priority: high)
- [x] Task-1.1: Remove or unify `_parse_method_patterns` from `cli.py` and ensure CLI uses `converter.helpers.parse_method_patterns` exclusively.
  - Files to edit: `splurge_unittest_to_pytest/cli.py`, `splurge_unittest_to_pytest/converter/helpers.py`
  - Tests: update or add unit test to assert CLI delegates to helpers and no duplicate parser exists.
  - Acceptance: `pytest` runs with no regression; any redundant `_parse_method_patterns` helper removed.

- [x] Task-1.2: Decide canonical fixture strategy (strict vs compat) and document decision.
  - Action: add short design doc in `docs/specs/spec-fixture-strategy-2025-09-17.md` describing strict-only vs compat behavior, and update `README.md`/`docs/README-DETAILS.md`.
  - Files to edit after decision: `splurge_unittest_to_pytest/stages/fixtures_stage.py`, `splurge_unittest_to_pytest/stages/rewriter_stage.py` (either remove in-class rewriting or make it conditional on compat flag).
  - Tests: add/adjust goldens under `tests/data` showing strict-mode outputs; add unit tests ensuring `fixtures_stage` drops classes when strict enabled.
  - Acceptance: updated docs explain behavior; tests/goldens updated.

- [ ] Task-1.3: Introduce `PipelineContext` (TypedDict) and refactor stage signatures to accept it.
  - Files to edit: `splurge_unittest_to_pytest/stages/__init__.py` (or a top-level `pipeline.py`), and each stage module under `stages/` and `converter/` that currently pass ad-hoc dicts.
  - Suggested type file: `splurge_unittest_to_pytest/types.py` with:
    - PipelineContext = TypedDict('PipelineContext', { 'path': Path, 'text': str, 'strict_mode': bool, ... })
  - Tests: run mypy; add unit tests for stage plumbing (simple in-memory stage runner exercising context keys).
  - Acceptance: mypy passes for modified files; no runtime regressions in tests.

Stage-2: Reliability and security (priority: high)
- [ ] Task-2.1: Implement atomic writes and `--encoding auto`.
  - Implement a small helper `splurge_unittest_to_pytest/io_helpers.py` exposing `atomic_write(path: Path, data: bytes|str, encoding: str|None)` and `detect_encoding(path: Path) -> str` (use stdlib `tokenize.open` behaviour or chardet if pinned in requirements).
  - Files to edit: `splurge_unittest_to_pytest/main.py` (replace file-write logic in `convert_file`), tests for atomic write scenarios in `tests/unit/test_io_helpers.py`.
  - Tests: simulate permission error/disk full using tmp_path and monkeypatch to validate no partial writes and proper error messages.
  - Acceptance: new tests pass; no partial files in error paths.

- [ ] Task-2.2: Harden `--output`/`--backup` handling and add hash-suffixed backups.
  - Files to edit: `splurge_unittest_to_pytest/cli.py`, `splurge_unittest_to_pytest/main.py` (backup creation logic).
  - Behavior: resolve paths with `Path.resolve()`, ensure output and backup are not system roots, and create backups with a content-hash suffix (e.g., `.bak-<sha256:8>`).
  - Tests: unit tests for path validation, backups created with unique hashed suffix, and identical input/output error handling.
  - Acceptance: tests for path validation and backup naming pass.

- [ ] Task-2.3: Add `--follow-symlinks/--no-follow-symlinks` and exclude globs with optional `--respect-gitignore`.
  - Files to edit: `splurge_unittest_to_pytest/cli.py`, `splurge_unittest_to_pytest/main.py` (discovery logic), and possibly add a dependency on `pathspec` for gitignore parsing if acceptable.
  - Tests: unit tests covering discovery with symlinked files and exclude/glob matching.
  - Acceptance: discovery behavior matches flags; unit tests pass.

Stage-3: UX improvements (priority: medium)
- [ ] Task-3.1: Add `--json` output and `--diff` dry-run option.
  - Files to edit: `splurge_unittest_to_pytest/cli.py`, `splurge_unittest_to_pytest/main.py`, and a new `splurge_unittest_to_pytest/reporting.py` for structured output.
  - JSON schema example: { path: str, changed: bool, errors: [str], summary: { asserts: int, lines_changed: int, imports_added: [str] } }
  - Tests: CLI integration tests verifying `--json` output shape and `--diff` produces unified diffs (use `difflib.unified_diff` for implementation and tests).
  - Acceptance: JSON output conforms to schema; `--diff` visible in dry-run tests.

- [ ] Task-3.2: Add `--jobs N` parallel conversion mode.
  - Files to edit: `splurge_unittest_to_pytest/cli.py`, `splurge_unittest_to_pytest/main.py` (executor plumbing), and reporting consolidation in `reporting.py`.
  - Behavior: use `concurrent.futures.ProcessPoolExecutor(max_workers=N)` with per-file atomic writes and process-safe backup naming; disable parallelism automatically when `--backup` writes to a non-process-safe location unless `--backup-shared` is provided.
  - Tests: parallel smoke tests in `tests/integration/test_parallel_smoke.py` asserting deterministic output ordering in consolidated summary and no inter-process write collisions.
  - Acceptance: integration tests pass; parallel mode documented.

Stage-4: Import injector enhancements (priority: medium)
- [ ] Task-4.1: Detect aliased imports and avoid duplicates; add optional alias normalization.
  - Files to edit: `splurge_unittest_to_pytest/converter/import_injector.py` (or `converter/injector_stage.py`).
  - Behavior: when scanning imports, detect `import pytest as pt` or `from pytest import mark as mk` and treat the module as present; provide an option `--normalize-pytest-alias` to rewrite local alias usages to `pytest` when safe.
  - Tests: unit tests for alias detection, and goldens for alias normalization when enabled.
  - Acceptance: no duplicate `pytest` imports inserted; alias tests pass.

- [ ] Task-4.2: Add tests for typing/pathlib merge scenarios.
  - Files to edit: `tests/unit/test_import_injector.py`, `tests/data/goldens/` as needed.
  - Acceptance: new tests pass and no regressions in existing goldens.

Testing & CI
- [ ] Task-5.1: Expand tests as described in the review — atomic writes, mixed-mode behavior, alias handling, parallel smoke tests, property-based transforms.
  - Suggested property-based tooling: `hypothesis` (add to `requirements-dev.txt` if accepted).
  - Acceptance: tests increased to cover new features; core coverage for stages remains >= 95%.

- [ ] Task-5.2: Run linters and typecheck: `ruff` and `mypy`.
  - Fix type issues introduced by PipelineContext refactor.
  - Acceptance: no new mypy/ruff errors in modified files.

Docs, changelog, and release
- [ ] Task-6.1: Update `README.md`, `docs/README-DETAILS.md`, and add `docs/specs/spec-fixture-strategy-2025-09-17.md` describing the chosen fixture strategy.
- [ ] Task-6.2: Document new CLI flags and JSON schema in `README.md` and `examples/` scripts.
- [ ] Task-6.3: Update `CHANGELOG.md` with breaking changes and new flags.

Sequencing and risk notes
- Perform Stage-1 changes first (policy) because they influence Stage-3/4 design. Stage-2 (atomic writes and path validation) is safety-critical and should be landed before enabling `--jobs` (Stage-3.2).
- Keep changes small and covered by unit tests. Prefer feature branches for larger refactors and open PRs per stage.

Acceptance checklist (summary)
- [ ] All existing tests run and pass (or updated goldens are accepted).
- [ ] New unit and integration tests for atomic writes, JSON output, diff mode, parallelism, and alias handling are implemented and pass.
- [ ] Docs updated with design decision on fixtures, new CLI flags, and JSON schema.

Appendix: Suggested quick file map
- `splurge_unittest_to_pytest/cli.py` — CLI flags, parsing and delegation to `main`.
- `splurge_unittest_to_pytest/main.py` — conversion pipeline entrypoint, file I/O, filesystem safety.
- `splurge_unittest_to_pytest/io_helpers.py` — atomic writes, encoding detection.
- `splurge_unittest_to_pytest/reporting.py` — structured JSON/diff output and consolidated summary.
- `splurge_unittest_to_pytest/types.py` — `PipelineContext` TypedDict and related shared types.
- `splurge_unittest_to_pytest/converter/import_injector.py` — import detection and normalization improvements.

``` 
