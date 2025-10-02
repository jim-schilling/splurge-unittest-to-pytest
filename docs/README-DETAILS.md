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
implemented with ``libcst``. The project features a **multi-pass analyzer**
that intelligently analyzes test patterns and applies transformations with
high confidence, preserving semantics where code mutates accumulators or
depends on loop ordering. The project aims to preserve test semantics and
readability while offering convenient preview and reporting options.

Features
--------
- **Multi-pass analyzer** that intelligently analyzes test patterns and applies
  transformations with high confidence, preserving semantics where code mutates
  accumulators or depends on loop ordering.
- **Enhanced pattern support**: Custom test prefixes (``spec_``, ``should_``, ``it_``),
  nested test classes, custom setup methods, and advanced exception handling.
- CST-based transformations using ``libcst`` for stable, semantics-preserving edits.
- Preserves class-structured tests that inherit from ``unittest.TestCase`` by default to
	maintain class scope and fixtures unless a conversion is explicitly requested.
- Converts common ``unittest`` assertions to Python ``assert`` statements or
	``pytest`` helpers when the conversion is safe and conservative.
- Merges ``setUp``/``tearDown`` into pytest fixtures where appropriate.
- **Configurable test discovery**: Supports custom test method prefixes and nested
  test class structures for modern testing frameworks.
- **Advanced setup/teardown detection**: Recognizes custom setup method patterns
  beyond standard ``setUp``/``tearDown``.
- **Enhanced exception handling**: Supports custom exception types, exception chaining,
  and advanced warning assertions.
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
	- **assertWarns -> ``with pytest.warns(WarningClass):`` when available**
	- **assertWarnsRegex -> ``with pytest.warns(WarningClass, match="regex"):``**
	- **Custom exception types**: Preserves custom exception classes (e.g., ``CustomError``) in transformations
	- **Exception chaining**: Supports ``assertRaises`` with additional callable arguments
	- **Custom warning types**: Preserves custom warning classes in ``assertWarns`` transformations

2. Test lifecycle and fixtures
	- ``setUp`` / ``tearDown`` methods -> converted into function-scoped ``pytest`` fixtures (``setup_method``/``teardown_method`` style is preserved when safer)
	- ``setUpClass`` / ``tearDownClass`` -> converted to class/module scoped fixtures where possible; conversion is conservative to avoid changing sharing semantics
	- ``setUpModule`` / ``tearDownModule`` -> converted to module-scoped fixtures
	- **Custom setup method detection**: Recognizes various setup method naming patterns:
	  - ``setup_method``, ``teardown_method`` (pytest-style)
	  - ``before_each``, ``after_each`` (common testing patterns)
	  - ``before``, ``after``, ``before_all``, ``after_all``
	  - ``initialize``, ``cleanup``, ``prepare``, ``finalize``
	  - ``set_up``, ``tear_down`` (snake_case variants)

3. Test discovery and structure
	- Tests in ``unittest.TestCase`` subclasses can be preserved as methods on the class or (optionally) converted into top-level ``pytest`` test functions when the transformation is safe and keeps semantics intact
	- **Custom test method prefixes**: Supports configurable test prefixes beyond ``test_`` (e.g., ``spec_``, ``should_``, ``it_``) for modern testing frameworks like BDD-style tests
	- **Nested test classes**: Properly handles test classes nested within other test classes, preserving the hierarchical structure in the transformed output
	- **Custom setup method detection**: Recognizes various setup method naming patterns beyond standard ``setUp``/``tearDown`` (e.g., ``setup_method``, ``before_each``, ``cleanup``)
	- ``subTest`` blocks: the transformer will attempt conservative conversions to parametrization only when the subtest usage is simple (e.g., iterating over a static list of inputs). Complex uses of loop variables, nested subtests, or dynamically generated cases will be left as-is and a warning will be emitted suggesting manual refactor to ``pytest.mark.parametrize``.

4. Test decorators and markers
	- ``@unittest.skip(reason)`` -> ``@pytest.mark.skip(reason=...)``
	- ``@unittest.skipIf(cond, reason)`` / ``@unittest.skipUnless`` -> ``pytest.mark.skipif`` conversions when the condition is a simple expression
	- ``@unittest.expectedFailure`` -> ``@pytest.mark.xfail`` (note: semantics differ; the tool documents any differences in the report)
	- **Custom exception types**: Preserves custom exception classes (e.g., ``CustomError``) in ``assertRaises`` transformations
	- **Exception chaining**: Supports ``assertRaises(Exception, func, arg1, arg2)`` with additional callable arguments
	- **Custom warning types**: Preserves custom warning classes in ``assertWarns`` transformations

5. Other helpers and patterns
	- ``self.assertLogs`` -> attempt to use ``caplog`` or ``pytest`` logging helpers when the context is simple; otherwise preserved with a note
	- ``unittest.mock.patch`` usage is preserved; simple context-manager or decorator uses may be converted to the same pattern under ``pytest`` (no behavioral change)
	- Common helper methods on ``TestCase`` that are purely assertion wrappers may be inlined when safe to improve readability; otherwise retained

Limitations and caveats
-----------------------
- Dynamic or metaprogrammed tests (tests generated at runtime, complex class factory patterns) are not reliably converted and are typically left unchanged.
- Custom ``TestCase`` subclasses that override discovery, run logic, or implement non-trivial helpers may prevent safe automatic conversion.
- The **multi-pass analyzer** intelligently handles ``subTest`` conversions: it uses sophisticated pattern analysis to determine when to apply ``parametrize`` vs ``subtests`` transformations, preserving semantics where code mutates accumulators or depends on loop ordering.
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

Custom test prefixes:

```py
# Before (spec_ prefix)
class TestCalculator(unittest.TestCase):
    def spec_should_add_numbers(self):
        self.assertEqual(add(1, 2), 3)

# After (preserved with spec_ prefix)
class TestCalculator:
    def spec_should_add_numbers(self):
        assert add(1, 2) == 3
```

Nested test classes:

```py
# Before
class TestAPI(unittest.TestCase):
    def test_basic_endpoint(self):
        pass

    class TestAuthentication(unittest.TestCase):
        def test_login_endpoint(self):
            pass

# After (preserved structure)
class TestAPI:
    def test_basic_endpoint(self):
        pass

    class TestAuthentication:
        def test_login_endpoint(self):
            pass
```

Custom setup methods:

```py
# Before
class TestExample(unittest.TestCase):
    def setup_method(self):
        self.value = 42

    def before_each(self):
        self.counter = 0

# After (preserved as-is)
class TestExample:
    def setup_method(self):
        self.value = 42

    def before_each(self):
        self.counter = 0
```

Enhanced exception handling:

```py
# Before
class CustomError(Exception):
    pass

class TestExample(unittest.TestCase):
    def test_custom_exception(self):
        def func():
            raise CustomError("custom message")

        self.assertRaises(CustomError, func)

    def test_warning_with_args(self):
        def func(message, category):
            warnings.warn(message, category)

        self.assertWarnsRegex(UserWarning, func, r"test \w+", "test message", UserWarning)

# After
class CustomError(Exception):
    pass

class TestExample:
    def test_custom_exception(self):
        def func():
            raise CustomError("custom message")

        with pytest.raises(CustomError):
            func()

    def test_warning_with_args(self):
        def func(message, category):
            warnings.warn(message, category)

        with pytest.warns(UserWarning, match=r"test \w+"):
            func("test message", UserWarning)
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
 - ``--skip-backup``: Skip creating a ``.backup`` copy of originals when writing (presence-only flag). By default the tool creates a ``.backup`` file next to the original when writing; if a ``.backup`` file already exists it will be preserved and not overwritten.
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
- ``--report / --no-report``: Generate a migration report (default: on).
- ``--report-format [json|html|markdown]``: Report format (default: json).
- ``--config FILE``: Load configuration from YAML file.
- ``--prefix PREFIX``: Allowed test method prefixes; repeatable (default: ``test``).
  Supports custom prefixes like ``spec``, ``should``, ``it`` for modern testing frameworks.

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

Write changes to a target directory (formatting always applied). Backups are created by default; to disable backups pass ``--skip-backup``:

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/ -r -t converted
# To disable backups when writing:
python -m splurge_unittest_to_pytest.cli migrate tests/ -r -t converted --skip-backup
```

Override extension (write `.txt` files instead of `.py`):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/test_example.py --ext txt
```

Migrate with custom test prefixes for modern testing frameworks:

```bash
# Support spec_ methods for BDD-style tests
python -m splurge_unittest_to_pytest.cli migrate tests/ --prefix spec --dry-run

# Support multiple prefixes for hybrid test suites
python -m splurge_unittest_to_pytest.cli migrate tests/ --prefix test --prefix spec --prefix should
```

Migrate with nested test class support:

```bash
# Automatically handles nested test classes
python -m splurge_unittest_to_pytest.cli migrate tests/ --dry-run --diff
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

Example: configure migration programmatically

```python
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig

config = MigrationConfig(
    dry_run=True,
    enable_decision_analysis=True,  # Multi-pass analyzer is always enabled
)
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

- **Enhanced pattern support** (October 2025): Comprehensive support for modern testing patterns:
  - **Custom test prefixes**: Configurable support for `spec_`, `should_`, `it_` and other prefixes beyond `test_`
  - **Nested test classes**: Proper handling of test classes nested within other test classes
  - **Advanced setup method detection**: Recognition of various setup method naming patterns (`setup_method`, `before_each`, `cleanup`, etc.)
  - **Enhanced exception handling**: Improved support for custom exception types, exception chaining, and advanced warning assertions
- **Multi-pass analyzer integration**: Implemented a sophisticated 5-pass analysis pipeline that intelligently determines transformation strategies for `subTest` loops, preserving semantics where code mutates accumulators or depends on loop ordering.
- The decision model is now always enabled for improved transformation accuracy and consistency.
- Expanded unit tests for assertion rewriting and string-fallbacks in the assert transformer.
