Title: splurge-unittest-to-pytest — review and recommendations (2025-09-17)

Objective
- Review the tool’s runtime, security, design, and tests. Recommend improvements and simplifications. Propose a staged action plan with acceptance criteria.

Executive summary
- Overall quality is high: clear CLI, strong staged pipeline, defensive diagnostics, extensive tests. Conversion logic is AST/CST-driven and avoids brittle string ops. Key areas to refine are: clarifying fixture handling between stages, import injection defaults, minor API/CLI cleanup, atomic file writes, and optional parallelization. Add a machine-readable output mode and strengthen edge-case tests.

Findings
- CLI
  - Uses Click with thoughtful options: dry-run, recursive, backup, output dir, encoding, custom method patterns, autocreate flag. Summaries and exit codes are consistent.
  - Minor duplication: `_parse_method_patterns` exists but CLI correctly uses `converter.helpers.parse_method_patterns`.
  - Dry-run: skips files already importing pytest; avoids noisy diffs but may hide mixed-mode conversions.
  - Diagnostics env gating is minimal and safe.

- Core API (`main.py`)
  - `ConversionResult` is clean. `convert_string`/`convert_file` implement robust CST/AST logic, including a late normalization sweep for `NAME.exception -> NAME.value`. PatternConfigurator provides a compact, future-proof extension surface.
  - `is_unittest_file` and `find_unittest_files` use practical heuristics and defensive I/O handling.

- Pipeline and stages
  - `StageManager` wraps stages with diagnostics writes guarded by env. Failsafe try/except protects pipeline.
  - Stage order is sensible: remove unittest artifacts → assertions → raises → generator → rewriter → fixtures → decorators/mock fixes → import injector → postvalidator → exceptioninfo normalizer → tidy.
  - `fixtures_stage` is “strict pytest” and drops classes while emitting top-level tests with fixture params. `rewriter_stage` also modifies in-class signatures; verify both are still necessary together.
  - `import_injector_stage` dedupes and orders imports deterministically and merges typing names.

- Testing
  - Comprehensive suite with unit and integration tests, golden files in `tests/data`, and coverage config in pyproject.
  - Examples folder shows basic and CLI usage.

Recommendations
- Simplification
  1) Remove or unify `_parse_method_patterns` in CLI; use only `converter.helpers.parse_method_patterns`.
  2) Decide on fixture strategy: If strict mode is the canonical path (drop classes and emit top-level tests), remove in-class signature rewriting from `rewriter_stage` or run it only when strict mode is disabled. Document the model clearly.
  3) Centralize policy around the canonical strict-only behavior and document any historical compatibility adapters as legacy; prune dead code paths related to legacy compatibility.

- Runtime hardening and reliability
  4) Adopt atomic writes in `convert_file`: write to `.<name>.tmp` then `replace()`; fsync as needed.
  5) Validate `--output` and `--backup` directories: create with appropriate perms; handle identical input/output with a clear message.
  6) Make backup creation robust: include a content hash suffix to avoid collisions and consider a `--no-backup` for explicit control.
  7) Improve Unicode handling: allow `--encoding auto` to chardet/`tokenize.open`-style detection; surface encoding errors with line/offset when available.
  8) Treat symlinks carefully during discovery; optionally add `--follow-symlinks/--no-follow-symlinks`.

- Security
  9) Ensure no writes occur outside intended directories: use `Path.resolve()` and verify `output`/`backup` are not parents of system roots. Backup file names use `Path.name`, which mitigates traversal; keep that.
  10) Diagnostics: when enabled, ensure directories are under a predictable, user-controlled location; document that env vars should only be set in trusted environments.

- UX and tooling
  11) Add `--format json` or `--json` to emit per-file results: {path, changed, errors[], summary{asserts, lines, imports_added}} for tool integration.
  12) Add `--diff` to print unified diffs in dry-run for changed files.
  13) Add `--jobs N` for parallel file conversion using `concurrent.futures.ProcessPoolExecutor` with a small work unit and consolidated reporting; disable when backups are used unless backup paths are made process-safe.
  14) Add `--exclude` globs and respect `.gitignore` optionally (`--respect-gitignore`).

- Import injector
  15) Make default behavior explicit: if no flags present, injector inserts `pytest`; if flags present, it only inserts requested imports. Document clearly in the API docstring and README.
  16) Extend import detection to handle aliased imports (`import pytest as pt`) and avoid reinsertion; optionally standardize on `pytest` name by rewriting usages when safe.

- Code quality
  17) MyPy/typing: keep strict mode; add precise types for pipeline context keys via a TypedDict (e.g., `PipelineContext`).
  18) Reduce broad except blocks where feasible; at least log at debug when diagnostics are enabled to aid troubleshooting.

- Documentation
  19) Expand README with a “Design” section describing the staged pipeline, strict policy, and extensibility points (PatternConfigurator, stage registration).
  20) Provide a migration note for users moving from mixed unittest/pytest to strict pytest output.

- Testing
  21) Add tests for aliased pytest/unittest imports and ensure no dupe inserts.
  22) Add tests for mixed-mode files (pytest present but some unittest patterns remain) to validate skip/convert behavior in both dry-run and write modes.
  23) Add tests for atomic write fallback scenarios (permission denied, disk full) to ensure graceful error reporting and no partial writes.
  24) Add tests for pattern configuration plumbing end-to-end through CLI → PatternConfigurator → stages.
  25) Add property-based tests for assertion/raises transforms with random whitespace and parenthesis permutations.
  26) Add parallel conversion smoke test to ensure determinism in output order and summary.

Staged action plan
- Stage-1: Policy and simplification
  - Task-1.1: Remove `_parse_method_patterns` from CLI, rely solely on helpers parser.
  - Task-1.2: Decide and document fixture strategy; if strict-only, gate or remove `rewriter_stage` adjustments that are made obsolete by `fixtures_stage`.
  - Task-1.3: Introduce `PipelineContext` TypedDict and refactor stage signatures to use it internally.
  - Acceptance: Tests pass unchanged or with updated goldens; docs updated.

- Stage-2: Reliability and security
  - Task-2.1: Implement atomic writes in `convert_file`; add `--encoding auto` option.
  - Task-2.2: Harden `--output`/`--backup` handling, resolve/validate paths, hash-suffixed backups.
  - Task-2.3: Optional `--follow-symlinks` and exclude globs; respect `.gitignore` under a flag.
  - Acceptance: New unit tests cover atomic writes, path validation, and symlink behavior.

- Stage-3: UX improvements
  - Task-3.1: Add `--json` output with per-file summary and `--diff` option.
  - Task-3.2: Add `--jobs` for parallel conversion with safe backup/output handling.
  - Acceptance: CLI integration tests validate JSON schema and parallel output determinism.

- Stage-4: Import injector enhancements
  - Task-4.1: Detect aliased imports and avoid duplicates; optional alias normalization.
  - Task-4.2: Tests for alias detection and typing/pathlib merge scenarios.
  - Acceptance: No regressions in existing goldens; new cases pass.

Testing strategy
- Use TDD for new flags and behaviors. Expand goldens where textual output is important (imports ordering). Add property-based tests for transforms. Keep coverage target ≥ 95% for core stages and API.

Acceptance criteria
- All existing tests pass, with updated goldens where policy is clarified.
- New tests validate atomic writes, JSON output, diff mode, parallelism, alias-handling, and pattern-config wiring.
- README and examples updated; CHANGELOG documents breaking changes and new flags.


