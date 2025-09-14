Plan: Fix generator wiring for temp-file fixtures and spacing issues
===============================================================

Date: 2025-09-14

Summary
-------
This plan addresses a conversion bug surfaced in `docs/issues-u2p-2025-sep-14-a.md` where the unittest->pytest conversion produced fixtures that returned bare filenames (e.g. `'test.sql'`) instead of absolute paths pointing to files created in the temporary directory. The converted tests then fail at runtime when code under test attempts to open the file relative to the current working directory.

Root cause
----------
- The unittest used `setUp()` to create temporary files and stored absolute paths on the test instance (e.g. `self.sql_file`). The converter extracted fixtures for `sql_file`/`schema_file` but produced fixtures that returned literal filenames (likely by converting simple attribute references into string fixtures) rather than returning the path that the helper wrote into the test's temp dir.
- Fixture wiring is missing: the helper fixture that actually calls `create_sql_with_schema` is `init_api_data()` but it is not used by the tests; the tests instead request `sql_file` and `schema_file` fixtures that are not connected to the created files.
- There are also code-style issues in the converted pytest file: missing/incorrect blank lines before/after function blocks and fixtures, likely due to the generator's blank-line emission rules.

Goals
-----
- Ensure converted fixtures which correspond to files created during setup return filesystem paths that point to the created files (prefer absolute paths).
- Ensure tests that depend on temporary directories use the `temp_dir` fixture and that file fixtures are either derived from `temp_dir` or documented to join `temp_dir` explicitly.
- Fix spacing blank-line emission rules around fixtures and top-level test functions so converted code is idiomatic and consistent.

Acceptance criteria
-------------------
- The conversion of the provided `TestInitAPI` unit test must preserve the original unittest semantics exactly: the converted pytest code must execute the same statements (in order) and produce the same observable effects (i.e. files created, return values assigned) as the original unittest would when run in the same environment.
- The converter must not "refactor" or infer higher-level intent (for example, it must not replace literal filename strings with inferred absolute paths unless that was already produced by the original code). Instead, it must reproduce the original statements so that subsequent runtime behavior is preserved.
- The converted output must have fixtures corresponding to `self` attributes when those attributes are set by explicit helper calls in `setUp`; the fixture bodies should call the same helper with the same arguments and return whatever that helper returned in the original test (literal or evaluated), preserving file-path values produced by the helper.
- The conversion generator emits acceptable blank-line spacing: at least one blank line between top-level fixtures and functions, and two blank lines between top-level class definitions (if present) and functions according to project styleguide. Spacing changes should be minimal and not alter code semantics.
- Add a unit/regression test to `tests/unit/` that encodes the original unittest and asserts the converted output contains fixtures that call `create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)` and return the helper's values (or the same string values assigned in the original `setUp`).

Proposed changes
----------------
1. Conversion wiring (preserve literal statements)
    - The converter must preserve original statements from `setUp()` when producing fixtures. Concretely:
       - If `setUp()` contains a call like `sql_file, schema_file = create_sql_with_schema(Path(self.temp_dir), 'test.sql', self.sql_content)` and then assigns `self.sql_file = str(sql_file)`, the converter should emit a fixture that executes the same helper call with the same arguments (using `temp_dir` fixture as necessary) and returns the helper's return values (or the literal `str(sql_file)` expression), rather than inventing or inferring alternate semantics.
       - Example generated fixture (preserving literal behavior):

```
@pytest.fixture
def init_api_data(temp_dir, sql_content):
   # Preserve the literal setUp statements: call the helper with the same args
   sql_file, schema_file = create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)
   try:
      yield sql_file, schema_file
   finally:
      # Preserve original tearDown semantics verbatim: emit the same statements
      # that the original test's `tearDown()` performed, mapping `self.*`
      # references to fixture parameters as needed. Do not invent implicit
      # cleanup behavior that wasn't present in the original test.
      # For example, if the original tearDown called `shutil.rmtree(self.temp_dir)`
      # the generated code should call `shutil.rmtree(temp_dir)` (name-mapped),
      # not a synthesized helper or different cleanup routine.
      import shutil

      shutil.rmtree(temp_dir, ignore_errors=True)
```

       - If the original test stored `self.sql_file = str(sql_file)`, the converter should either emit `sql_file = str(sql_file)` inside the fixture or expose a separate fixture that returns `str(sql_file)` — but it must be the equivalent of the original statement.

    - The converter should not rewrite tests to request a different fixture name (for example, changing call-sites to use `init_api_data.sql_file`); instead it should continue to provide fixtures named after the original attributes (e.g. `sql_file`, `schema_file`) if the original test referenced `self.sql_file`.

2. Fixture wiring rules
   - Update the name-resolution step so that the converter links files created in the setup helper with the fixtures that should expose them. This may require a small dataflow pass that detects assignments to `self.<name>` that are paths returned by helper calls.

3. Spacing rules
   - Update the blank-line emission in the generator so that between consecutive top-level fixtures and functions there is a single blank line, and between groups of top-level declarations (e.g., fixture group vs test function group) a consistent separator (1-2 blank lines) as configured in project style.

4. Tests and regression
    - Add a regression test that embeds the UNITTEST source (or loads it from `docs/`) and validates that the converted pytest code contains fixture definitions that call `create_sql_with_schema(Path(temp_dir), 'test.sql', sql_content)` and then return or assign `str(sql_file)` / `str(schema_file)` in the same manner as the original `setUp` (i.e., the literal statements are preserved).

Implementation sketch
--------------------
- Add a conservative dataflow detector in `converter/fixture_builder.py` that recognizes `self.<name> = <expr>` patterns where `<expr>` is a direct call or expression and records the exact RHS expression. When converting, emit fixture code that executes the same RHS expression (adapting names like `self.temp_dir` → `temp_dir`) rather than substituting inferred higher-level semantics.
- Update `fixture_builder` so that when `self.<name>` is assigned by the RHS of a helper call, the generated fixture executes the same helper call with the same syntactic arguments (mapping `self.temp_dir` -> `temp_dir` fixture) and returns the same derived value (e.g., `str(sql_file)` if that was the original statement).
- Add unit tests in `tests/unit/test_converter_fixtures.py` validating both code generation (string matching of emitted fixture) and behavior (run the converted code in a temp dir or execute the generator on the sample unittest and compile/exec the output to assert fixtures return expected paths).

Risk and mitigation
-------------------
- Risk: Aggressive dataflow matching may mis-detect unrelated `self` attribute assignments. Mitigation: only match patterns where the right-hand side is a direct call to a helper like `create_*` or where the RHS is a `Path(...)`, `str(...)`, or `os.path.join` of known temp_dir values.
- Risk: Changing generator spacing may affect many golden tests. Mitigation: keep spacing changes minimal; update golden test expectations in a batch and run the test suite to ensure no regressions.

Next steps
----------
1. Implement the literal-preservation fixture wiring in the converter (conservative dataflow mapping + emission of RHS expressions verbatim, with `self.*` → fixture parameter mapping).
2. Add the regression test (see `tests/unit/test_fix_init_api_conversion.py`) and run the test suite.
3. If spacing issues remain, create a small follow-up to adjust blank-line emission and update golden tests — but keep spacing changes minimal to avoid noisy golden updates.

Contact
-------
If you want I can implement steps 1 and 2 now, run the test suite, and report results. Otherwise, we can discuss the preferred approach for fixtures-as-named-tuples vs separate fixtures.
