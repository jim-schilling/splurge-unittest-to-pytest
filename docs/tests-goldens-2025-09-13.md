# Tests & Goldens Plan — 2025-09-13

This document enumerates the proposed tests and golden files to add or update to validate the converter's canonical pytest output.

Principles
- Each sample pair (unittest input -> pytest expected) in `tests/data/samples` should have a unit test that runs the conversion pipeline and asserts the produced source equals the `*-pytest.txt` canonical output exactly (normalized for trailing whitespace and consistent import ordering).
- Tests should be deterministic and small. Use an explicit pipeline runner that replicates the same stages used in CI: collector -> generator -> import_injector -> tidy/format.
- When a sample requires non-trivial behavior (setUp/tearDown grouping, typing import injection, patch decorator lifting), add a focused unit test that asserts those behaviors (not only full-file equality) to make diagnostics clear when failures occur.

Test/golden list

1) Sample 01 (simple temp dir & file)
- Unittest: `tests/data/samples/sample-01-unittest.txt`
- Golden/expected: `tests/data/samples/sample-01-pytest.txt`
- Unit test: `tests/unit/test_sample_01_conversion.py`
- Assertion: strict equality of produced code to golden (after normalizing whitespace). Also assert presence of `@pytest.fixture` and that `test_file` fixture uses `return` (not yield).
- Priority: High

2) Sample 02 (sqlite3 + patch)
- Unittest: `tests/data/samples/sample-02-unittest.txt`
- Golden/expected: `tests/data/samples/sample-02-pytest.txt`
- Unit test: `tests/unit/test_sample_02_conversion.py`
- Assertion: strict equality; additional asserts that `db_connection` fixture is a generator (yields) and annotated as `sqlite3.Connection`, `cursor` fixture returns `sqlite3.Cursor`, and `@patch('logging.getLogger')` appears above `test_user_logging` function.
- Priority: High

3) Sample 03 (mocking and simple fixtures) - if present in samples folder
- Unittest: `tests/data/samples/sample-03-unittest.txt`
- Golden/expected: `tests/data/samples/sample-03-pytest.txt`
- Unit test: `tests/unit/test_sample_03_conversion.py`
- Assertion: strict equality; assert small fixtures use direct return when possible.
- Priority: Medium

4) Sample 04 (complex temp dirs & env + multiple fixtures)
- Unittest: `tests/data/samples/sample-04-unittest.txt`
- Golden/expected: `tests/data/samples/sample-04-pytest.txt`
- Unit test: `tests/unit/test_sample_04_conversion.py`
- Assertion: strict equality; explicit assertions for:
  - per-attribute fixtures for temporary directories (for example `temp_dir`, `config_dir`, `data_dir`, `log_dir`) where each fixture performs its own setup and cleanup (yield + finally or return as appropriate). The generator intentionally avoids producing a single composite `temp_dirs` fixture.
  - `mock_env` fixture uses yield and restores environment in finally
  - `main_config` fixture returns a dict and uses the appropriate per-attribute fixtures (e.g., `temp_dir`) in its body rather than a composite `temp_dirs` mapping
- Priority: High

5) Other samples (05–09) if present
- For each sample-N with `sample-N-unittest.txt` and `sample-N-pytest.txt` add:
  - `tests/unit/test_sample_N_conversion.py`
  - Assertion: strict equality of full-file conversion and targeted asserts for fixture return types, decorator forms, or patch handling as appropriate.
- Priority: Medium

6) test_init_api conversion verification
- Unittest backup: `tests/data/test_init_api.py.bak.txt`
- Converted file in repo: `tests/data/test_init_api_converted.py` (existing)
- Unit test: `tests/unit/test_init_api_converted_matches_expected.py`
- Assertion: Compare produced conversion from the backup file against `tests/data/test_init_api_converted.py` (strict equality), and assert that typing imports include `Dict` or `Any` where expected.
- Priority: Low (smoke check)

Supporting helpers
- Create `tests/unit/helpers/convert_and_normalize.py` with a small helper function `convert_text_and_normalize(src_text: str) -> str` that runs the project's conversion pipeline and returns normalized source (strip trailing whitespace, normalize line endings to \n, and canonical import order for typing import insertion). Use this helper across sample tests.
- Create `tests/unit/test_conversion_utils.py` that tests this helper on a trivial snippet.

Failure diagnostics
- When strict equality fails, tests should print a short unified diff of produced vs expected and assert additional targeted conditions (presence of `@pytest.fixture`, presence/absence of `yield`, expected typing import). This will aid quick triage.

Implementation notes & runner
- Use pytest for these unit tests (project already uses pytest).
- Keep tests fast by running conversion functions directly in-process rather than invoking CLI.
- Normalize produced source by running it through the project's tidy/format stage (or libcst codegen) to ensure formatting is deterministic.

Commit strategy
- Add goldens and unit tests in one commit.
- Implement converter code changes incrementally in subsequent commits, each accompanied by running the newly added unit tests and updating goldens if the change is intentional.

Checklist before merging
- All new unit tests pass locally.
- Ruff and mypy pass (fix any simple lint/type issues introduced).
- Update `CHANGELOG.md` with a short summary of converter changes.


