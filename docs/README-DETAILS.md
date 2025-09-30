# splurge-unittest-to-pytest — Detailed Reference

This document provides a comprehensive reference for the tool including
features, CLI flags, examples, programmatic API usage, safety notes, and
developer guidance.

Table of contents
- Overview
- Features
- Supported unittest to pytest conversion candidates
- CLI reference
- Examples (CLI and programmatic)
- Programmatic API
- Safety and limitations
- Developer notes

Overview
--------
``splurge-unittest-to-pytest`` converts Python ``unittest``-style tests to
``pytest``-style tests using conservative, AST/CST-based transformations
implemented with ``libcst``. The project aims to preserve test semantics and
readability while offering convenient preview and reporting options.

Features
--------
- CST-based transformations using ``libcst`` for stable, semantics-preserving edits.
- Preserves class-structured tests that inherit from ``unittest.TestCase`` by default to
	maintain class scope and fixtures unless a conversion is explicitly requested.
- Converts common ``unittest`` assertions to Python ``assert`` statements or
	``pytest`` helpers when the conversion is safe and conservative.
- Merges ``setUp``/``tearDown`` into pytest fixtures where appropriate.
- Dry-run modes: show generated code, unified diffs (``--diff``), or file lists (``--list``).
- Generated code is always formatted with ``isort`` and ``black`` before writing.
- Import optimization and safe removal of unused ``unittest`` imports while
	detecting dynamic import patterns to avoid unsafe removals.

Supported unittest to pytest conversion candidates
-----------------------------------------------
This section summarizes the common ``unittest`` APIs and patterns the tool
will attempt to convert automatically. The transformations are conservative
— we only rewrite constructs when we can preserve semantics with high
confidence. Where conversions are ambiguous the tool prefers a readable
fallback and records warnings in the migration report.

1. Assertion rewriting
	- assertEqual(a, b) -> assert a == b
	- assertNotEqual(a, b) -> assert a != b
	- assertTrue(x) -> assert x
	- assertFalse(x) -> assert not x
	- assertIs(a, b) -> assert a is b
	- assertIsNot(a, b) -> assert a is not b
	- assertIsNone(x) -> assert x is None
	- assertIsNotNone(x) -> assert x is not None
	- assertIn(a, b) -> assert a in b
	- assertNotIn(a, b) -> assert a not in b
	- assertGreater(a, b) / assertLess / assertGreaterEqual / assertLessEqual -> corresponding comparison asserts
	- assertRaises(Exception, callable, *args, **kwargs) -> use ``with pytest.raises(Exception): callable(*args, **kwargs)`` when the call site is simple
	- assertRaises as a context manager -> ``with pytest.raises(Exception):`` (preserved)
	- assertRaisesRegex -> ``with pytest.raises(Exception, match="regex"):``
	- assertWarns -> ``with pytest.warns(WarningClass):`` when available

2. Test lifecycle and fixtures
	- ``setUp`` / ``tearDown`` methods -> converted into function-scoped ``pytest`` fixtures (``setup_method``/``teardown_method`` style is preserved when safer)
	- ``setUpClass`` / ``tearDownClass`` -> converted to class/module scoped fixtures where possible; conversion is conservative to avoid changing sharing semantics
	- ``setUpModule`` / ``tearDownModule`` -> converted to module-scoped fixtures

3. Test discovery and structure
	- Tests in ``unittest.TestCase`` subclasses can be preserved as methods on the class or (optionally) converted into top-level ``pytest`` test functions when the transformation is safe and keeps semantics intact
	- ``subTest`` blocks: the transformer will attempt conservative conversions to parametrization only when the subtest usage is simple (e.g., iterating over a static list of inputs). Complex uses of loop variables, nested subtests, or dynamically generated cases will be left as-is and a warning will be emitted suggesting manual refactor to ``pytest.mark.parametrize``.

4. Test decorators and markers
	- ``@unittest.skip(reason)`` -> ``@pytest.mark.skip(reason=...)``
	- ``@unittest.skipIf(cond, reason)`` / ``@unittest.skipUnless`` -> ``pytest.mark.skipif`` conversions when the condition is a simple expression
	- ``@unittest.expectedFailure`` -> ``@pytest.mark.xfail`` (note: semantics differ; the tool documents any differences in the report)

5. Other helpers and patterns
	- ``self.assertLogs`` -> attempt to use ``caplog`` or ``pytest`` logging helpers when the context is simple; otherwise preserved with a note
	- ``unittest.mock.patch`` usage is preserved; simple context-manager or decorator uses may be converted to the same pattern under ``pytest`` (no behavioral change)
	- Common helper methods on ``TestCase`` that are purely assertion wrappers may be inlined when safe to improve readability; otherwise retained

Limitations and caveats
-----------------------
- Dynamic or metaprogrammed tests (tests generated at runtime, complex class factory patterns) are not reliably converted and are typically left unchanged.
- Custom ``TestCase`` subclasses that override discovery, run logic, or implement non-trivial helpers may prevent safe automatic conversion.
- Converting ``subTest`` to ``parametrize`` is conservative: the transformer only attempts this when the inputs are statically discoverable and the loop body is side-effect free.
- Any conversion that may alter test ordering, scoping, or shared mutable state (for example, complex class-level fixtures) is avoided or flagged for manual review.
- The semantics of ``expectedFailure`` differ slightly between ``unittest`` and ``pytest.xfail``; when a conversion is applied the tool documents the change in the migration report so users can verify intent.

Examples
--------
Simple assertion conversion:

```py
# Before (unittest)
self.assertEqual(result, expected)

# After (pytest)
assert result == expected
```

Simple assertRaises conversion (callable form -> context manager form):

```py
# Before
self.assertRaises(ValueError, func, arg)

# After
with pytest.raises(ValueError):
	 func(arg)
```

Subtest -> parametrize (only when safe):

```py
# Before
for inp, expected in [(1, 2), (3, 4)]:
	 with self.subTest(inp=inp):
		  self.assertEqual(func(inp), expected)

# After (parametrize)
@pytest.mark.parametrize("inp,expected", [(1, 2), (3, 4)])
def test_func(inp, expected):
	 assert func(inp) == expected
```

CLI reference
-------------
All flags are available on the ``migrate`` command. Summary below; use
``--help`` for the authoritative list.

- ``-d, --dir DIR``: Root directory for input discovery.
- ``-f, --file PATTERN``: Glob pattern(s) to select files (repeatable). Default: ``test_*.py``.
- ``-r, --recurse / --no-recurse``: Recurse directories (default: recurse).
- ``-t, --target-dir DIR``: Directory to write outputs.
- ``--preserve-structure / --no-preserve-structure``: Preserve original directory layout (default: preserve).
 - ``--backup``: Create a ``.backup`` copy of originals when writing (presence-only flag; default: off).
- ``--line-length N``: Max line length used by formatters (default: 120).
- ``--dry-run``: Do not write files; return or display generated output.
	- With ``--dry-run --diff``: show unified diffs.
	- With ``--dry-run --list``: list files only.
- ``--ext EXT``: Override the target file extension.
- ``--suffix SUFFIX``: Append suffix to target filename stem when writing.
- ``--fail-fast``: Stop on first error (default: off).
 - ``-v, --verbose``: Verbose logging (presence-only flag). Note: ``--verbose`` and ``--quiet`` are mutually exclusive; do not pass both.
 - ``--dry-run``: Do not write files; return or display generated output (presence-only flag).
	 - With ``--dry-run --diff``: show unified diffs (``--diff`` is presence-only).
	 - With ``--dry-run --list``: list files only (``--list`` is presence-only).
 - ``--diff``: Show unified diffs in dry-run mode (presence-only flag).
 - ``--list``: List files only in dry-run mode (presence-only flag).
 - ``--posix``: Format displayed file paths using POSIX separators when True (presence-only flag).
 - ``--fail-fast``: Stop on first error (presence-only flag).
 - ``--parametrize``: Attempt conservative subTest -> parametrize conversions (presence-only flag). NOTE: this flag is deprecated in favor of the clearer ``--subtest`` flag described below.
 - ``--subtest``: Presence-only flag. When present the converter will attempt to generate pytest code that preserves ``unittest.subTest`` semantics using the ``subtests`` fixture (from ``pytest-subtests``) or a compatibility shim. When ``--subtest`` is not provided the tool defaults to parametrize-style conversions (i.e., generate ``@pytest.mark.parametrize`` when safe).
- ``--report / --no-report``: Generate a migration report (default: on).
- ``--report-format [json|html|markdown]``: Report format (default: json).
- ``--config FILE``: Load configuration from YAML file.
- ``--prefix PREFIX``: Allowed test method prefixes; repeatable (default: ``test``).

Examples
--------

Preview a single file (print converted code):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/test_example.py --dry-run
```

Show unified diffs for a directory:

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/ -r --dry-run --diff
```

Write changes to a target directory with backups (formatting always applied):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/ -r -t converted --backup
```

Override extension (write `.txt` files instead of `.py`):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/test_example.py --ext txt
```

Programmatic API
-----------------

Use :func:`splurge_unittest_to_pytest.main.migrate` for programmatic migration:

```python
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig

config = MigrationConfig(dry_run=True)
result = main.migrate(["tests/test_example.py"], config=config)
if result.is_success():
		gen_map = result.metadata.get("generated_code", {})
		print(gen_map)
else:
		print("Migration failed:", result.error)
```

The function returns a :class:`Result` that contains migrated paths and
optional metadata. When ``dry_run`` is enabled the result metadata often
includes a ``generated_code`` mapping of target paths to code strings.

Example: enable subtest-preserving mode programmatically

```python
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig

config = MigrationConfig(dry_run=True, subtest=True)
result = main.migrate(["tests/test_example.py"], config=config)
if result.is_success():
	gen_map = result.metadata.get("generated_code", {})
	print(gen_map)
else:
	print("Migration failed:", result.error)
```

Safety and limitations
----------------------

- The tool targets common and idiomatic ``unittest`` patterns. Highly
	dynamic code, metaprogramming, or uncommon testing patterns may not be
	fully convertible automatically.
- Always inspect conversions (use ``--dry-run --diff``) and run your
	project tests after migration. The tool aims to be conservative and
	preserve behavior, but automated transformations require manual
	verification in complex cases.

Note on top-level __main__ guards and runtime test invocations
------------------------------------------------------------

- The transformer removes top-level ``if __name__ == "__main__":`` guard
	blocks and any top-level calls to ``unittest.main()`` or ``pytest.main()``.
	This avoids emitting runtime test-invocation code in transformed files.
	The expectation is that tests are executed via the command line or a
	test runner (for example, ``pytest``). If you need to preserve these
	guards for runnable transformed files, please open an issue or feature
	request — there is no preservation option in the current release.

Developer notes
---------------

- Tests: run ``python -m pytest -q`` to execute the full test suite.
- Formatting / linting: use ``python -m ruff check --fix`` and
	``python -m ruff format``.
- Architecture: the pipeline is organized as Jobs → Tasks → Steps, each
	with a single responsibility. See the source under ``splurge_unittest_to_pytest/`` for
	concrete implementations.
- Assertion transformer helpers: ``assert_transformer.py`` now exposes
	plain functions such as ``_rewrite_expression`` and
	``_rewrite_unary_operation`` backed by a metadata-aware
	``parenthesized_expression`` helper. Focused tests in
	``tests/unit/test_assert_transformer_expression_rewrites.py`` cover
	positive, negative, and edge-case flows for these helpers.
- Contributions: open a PR against the ``main`` branch and include tests
	for new behavior. Keep changes small and run the full suite before
	requesting review.

Recent updates
--------------

- Expanded unit tests for assertion rewriting and string-fallbacks in the
	assert transformer.
- Improved dry-run presentation and added unified-diff output.

