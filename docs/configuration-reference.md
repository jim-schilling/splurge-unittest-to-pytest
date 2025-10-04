# Configuration Reference
This document provides comprehensive reference for all configuration options.
Auto-generated from the configuration metadata system.

## Table of Contents

- [Output Settings](#output-settings)
- [Transformation Settings](#transformation-settings)
- [Import Handling](#import-handling)
- [Transform Selection](#transform-selection)
- [Processing Options](#processing-options)
- [Advanced Options](#advanced-options)
- [Test Method Patterns](#test-method-patterns)
- [Parametrize Settings](#parametrize-settings)
- [Degradation Settings](#degradation-settings)

## Output Settings

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `backup_root` | `str | None` | `None` | 🟢 optional | Directory where backup files will be stored. If None, backups are stored alongside originals. || `root_directory` | `str | None` | `None` | 🟢 optional | Root directory to scan for test files. If None, uses current working directory. || `target_extension` | `str | None` | `None` | 🟢 optional | File extension for transformed files. If None, uses original extension. || `target_suffix` | `str` | `` | 🟢 optional | Suffix to append to transformed filenames (used when target_root is None). || `backup_originals` | `bool` | `True` | 🟡 recommended | Whether to create backup copies of original files before transformation. || `recurse_directories` | `bool` | `True` | 🟡 recommended | Whether to recursively scan subdirectories for test files. || `target_root` | `str | None` | `None` | 🟡 recommended | Root directory where transformed files will be written. If None, files are written alongside originals with a suffix. || `file_patterns` | `list[str]` | `['test_*.py']` | 🔴 required | Glob patterns to match test files for transformation. |### `backup_originals`

**Type:** `bool`
**Default:** `True`
**Importance:** Recommended

Whether to create backup copies of original files before transformation.

**CLI Flag:** `--backup-originals`

**Environment Variable:** `SPLURGE_BACKUP_ORIGINALS`

**Examples:**
- `true`- `false`**Related Fields:**
- `backup_root`**Common Mistakes:**
- Disabling backups thinking they're not needed- Not having enough disk space for backups---

### `backup_root`

**Type:** `str | None`
**Default:** `None`
**Importance:** Optional

Directory where backup files will be stored. If None, backups are stored alongside originals.

**CLI Flag:** `--backup-root`

**Environment Variable:** `SPLURGE_BACKUP_ROOT`

**Examples:**
- `./backups`- `/tmp/backups`- `original_tests`**Constraints:**
- Must be writable if specified- Cannot be used when backup_originals=False**Related Fields:**
- `backup_originals`**Common Mistakes:**
- Using the same directory as target_root- Not having write permissions to the backup directory---

### `file_patterns`

**Type:** `list[str]`
**Default:** `['test_*.py']`
**Importance:** Required

Glob patterns to match test files for transformation.

**CLI Flag:** `--file-patterns`

**Environment Variable:** `SPLURGE_FILE_PATTERNS`

**Examples:**
- `test_*.py`- `['test_*.py', 'spec_*.py']`- `**/test_*.py`**Constraints:**
- At least one pattern required- Must be valid glob patterns**Related Fields:**
- `root_directory`- `recurse_directories`**Common Mistakes:**
- Using regex instead of glob patterns- Forgetting wildcards (*, **, ?)- Not including .py extension---

### `recurse_directories`

**Type:** `bool`
**Default:** `True`
**Importance:** Recommended

Whether to recursively scan subdirectories for test files.

**CLI Flag:** `--recurse-directories`

**Environment Variable:** `SPLURGE_RECURSE_DIRECTORIES`

**Examples:**
- `true`- `false`**Related Fields:**
- `root_directory`- `file_patterns`**Common Mistakes:**
- Setting to false when you have nested test directories- Not understanding this affects the entire directory tree---

### `root_directory`

**Type:** `str | None`
**Default:** `None`
**Importance:** Optional

Root directory to scan for test files. If None, uses current working directory.

**CLI Flag:** `--root-directory`

**Environment Variable:** `SPLURGE_ROOT_DIRECTORY`

**Examples:**
- `./tests`- `src/tests`- `/path/to/project/tests`**Constraints:**
- Must be a readable directory if specified**Related Fields:**
- `file_patterns`- `recurse_directories`**Common Mistakes:**
- Using a path that doesn't exist- Forgetting this is the scan root, not just a subdirectory---

### `target_extension`

**Type:** `str | None`
**Default:** `None`
**Importance:** Optional

File extension for transformed files. If None, uses original extension.

**CLI Flag:** `--target-extension`

**Environment Variable:** `SPLURGE_TARGET_EXTENSION`

**Examples:**
- `.py`- `.pytest.py`**Constraints:**
- Must be a valid file extension if specified**Related Fields:**
- `target_suffix`**Common Mistakes:**
- Including the dot in the extension- Using an extension that conflicts with the target language---

### `target_root`

**Type:** `str | None`
**Default:** `None`
**Importance:** Recommended

Root directory where transformed files will be written. If None, files are written alongside originals with a suffix.

**CLI Flag:** `--target-root`

**Environment Variable:** `SPLURGE_TARGET_ROOT`

**Examples:**
- `./output`- `/tmp/migrated`- `migrated_tests`**Constraints:**
- Must be a writable directory if specified- Cannot be used with dry_run=True**Related Fields:**
- `dry_run`- `target_suffix`- `target_extension`**Common Mistakes:**
- Using a relative path that doesn't exist- Forgetting to create the directory first- Using the same directory as source files without a suffix---

### `target_suffix`

**Type:** `str`
**Default:** ``
**Importance:** Optional

Suffix to append to transformed filenames (used when target_root is None).

**CLI Flag:** `--target-suffix`

**Environment Variable:** `SPLURGE_TARGET_SUFFIX`

**Examples:**
- `_pytest`- `_migrated`- `.new`**Related Fields:**
- `target_root`- `target_extension`**Common Mistakes:**
- Using characters that aren't valid in filenames- Not understanding this creates new files alongside originals---

## Transformation Settings

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `assert_almost_equal_places` | `int` | `7` | 🟢 optional | Default decimal places for assertAlmostEqual transformations. || `fail_fast` | `bool` | `False` | 🟢 optional | Stop processing on the first error encountered. || `line_length` | `int | None` | `120` | 🟢 optional | Maximum line length for formatted output code. || `log_level` | `str` | `INFO` | 🟢 optional | Logging verbosity level for transformation process. || `max_file_size_mb` | `int` | `10` | 🟢 optional | Maximum file size to process in megabytes. || `dry_run` | `bool` | `False` | 🟡 recommended | Perform a dry run without writing any files. |### `assert_almost_equal_places`

**Type:** `int`
**Default:** `7`
**Importance:** Optional

Default decimal places for assertAlmostEqual transformations.

**CLI Flag:** `--assert-almost-equal-places`

**Environment Variable:** `SPLURGE_ASSERT_ALMOST_EQUAL_PLACES`

**Examples:**
- `7`- `3`- `10`**Constraints:**
- Must be between 1-15**Common Mistakes:**
- Using too few places for floating point comparisons- Not understanding this affects precision of generated tests---

### `dry_run`

**Type:** `bool`
**Default:** `False`
**Importance:** Recommended

Perform a dry run without writing any files.

**CLI Flag:** `--dry-run`

**Environment Variable:** `SPLURGE_DRY_RUN`

**Examples:**
- `true`- `false`**Constraints:**
- Cannot be used with target_root**Related Fields:**
- `target_root`**Common Mistakes:**
- Thinking dry run still creates output files- Not using dry run when testing new configurations---

### `fail_fast`

**Type:** `bool`
**Default:** `False`
**Importance:** Optional

Stop processing on the first error encountered.

**CLI Flag:** `--fail-fast`

**Environment Variable:** `SPLURGE_FAIL_FAST`

**Examples:**
- `true`- `false`**Related Fields:**
- `continue_on_error`**Common Mistakes:**
- Using in CI when you want to see all errors- Not using when debugging a single failing file---

### `line_length`

**Type:** `int | None`
**Default:** `120`
**Importance:** Optional

Maximum line length for formatted output code.

**CLI Flag:** `--line-length`

**Environment Variable:** `SPLURGE_LINE_LENGTH`

**Examples:**
- `120`- `100`- `80`**Constraints:**
- Must be between 60-200 if specified**Related Fields:**
- `format_output`**Common Mistakes:**
- Setting too low causing excessive line breaks- Not understanding this only affects formatted output---

### `log_level`

**Type:** `str`
**Default:** `INFO`
**Importance:** Optional

Logging verbosity level for transformation process.

**CLI Flag:** `--log-level`

**Environment Variable:** `SPLURGE_LOG_LEVEL`

**Examples:**
- `INFO`- `DEBUG`- `WARNING`**Constraints:**
- Must be one of: DEBUG, INFO, WARNING, ERROR**Common Mistakes:**
- Using DEBUG in production causing log spam- Not increasing verbosity when troubleshooting issues---

### `max_file_size_mb`

**Type:** `int`
**Default:** `10`
**Importance:** Optional

Maximum file size to process in megabytes.

**CLI Flag:** `--max-file-size-mb`

**Environment Variable:** `SPLURGE_MAX_FILE_SIZE_MB`

**Examples:**
- `10`- `50`- `5`**Constraints:**
- Must be between 1-100**Common Mistakes:**
- Setting too low for large test files- Setting too high causing memory issues---

## Import Handling

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `preserve_import_comments` | `bool` | `True` | 🟢 optional | Whether to preserve comments in import sections. || `format_output` | `bool` | `True` | 🟡 recommended | Whether to format output code with black and isort. || `remove_unused_imports` | `bool` | `True` | 🟡 recommended | Whether to remove unused unittest imports after transformation. |### `format_output`

**Type:** `bool`
**Default:** `True`
**Importance:** Recommended

Whether to format output code with black and isort.

**CLI Flag:** `--format-output`

**Environment Variable:** `SPLURGE_FORMAT_OUTPUT`

**Examples:**
- `true`- `false`**Related Fields:**
- `line_length`**Common Mistakes:**
- Disabling when you want consistent code formatting- Not having black/isort installed when enabled---

### `preserve_import_comments`

**Type:** `bool`
**Default:** `True`
**Importance:** Optional

Whether to preserve comments in import sections.

**CLI Flag:** `--preserve-import-comments`

**Environment Variable:** `SPLURGE_PRESERVE_IMPORT_COMMENTS`

**Examples:**
- `true`- `false`**Related Fields:**
- `transform_imports`**Common Mistakes:**
- Disabling when you have important import comments- Not understanding this preserves comment positioning---

### `remove_unused_imports`

**Type:** `bool`
**Default:** `True`
**Importance:** Recommended

Whether to remove unused unittest imports after transformation.

**CLI Flag:** `--remove-unused-imports`

**Environment Variable:** `SPLURGE_REMOVE_UNUSED_IMPORTS`

**Examples:**
- `true`- `false`**Related Fields:**
- `transform_imports`**Common Mistakes:**
- Disabling when you want clean imports- Not understanding this only affects unittest imports---

## Transform Selection

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `transform_subtests` | `bool` | `True` | 🟢 optional | Whether to attempt subTest conversions to pytest parametrize. || `transform_setup_teardown` | `bool` | `True` | 🟡 recommended | Whether to convert setUp/tearDown methods to pytest fixtures. || `transform_skip_decorators` | `bool` | `True` | 🟡 recommended | Whether to convert unittest skip decorators to pytest equivalents. || `transform_assertions` | `bool` | `True` | 🔴 required | Whether to transform unittest assertions to pytest equivalents. || `transform_imports` | `bool` | `True` | 🔴 required | Whether to transform unittest imports to pytest equivalents. |### `transform_assertions`

**Type:** `bool`
**Default:** `True`
**Importance:** Required

Whether to transform unittest assertions to pytest equivalents.

**CLI Flag:** `--transform-assertions`

**Environment Variable:** `SPLURGE_TRANSFORM_ASSERTIONS`

**Examples:**
- `true`- `false`**Common Mistakes:**
- Disabling when you want full unittest to pytest conversion- Not understanding this is the core transformation---

### `transform_imports`

**Type:** `bool`
**Default:** `True`
**Importance:** Required

Whether to transform unittest imports to pytest equivalents.

**CLI Flag:** `--transform-imports`

**Environment Variable:** `SPLURGE_TRANSFORM_IMPORTS`

**Examples:**
- `true`- `false`**Related Fields:**
- `remove_unused_imports`**Common Mistakes:**
- Disabling when you want full import conversion- Not understanding this affects import statements---

### `transform_setup_teardown`

**Type:** `bool`
**Default:** `True`
**Importance:** Recommended

Whether to convert setUp/tearDown methods to pytest fixtures.

**CLI Flag:** `--transform-setup-teardown`

**Environment Variable:** `SPLURGE_TRANSFORM_SETUP_TEARDOWN`

**Examples:**
- `true`- `false`**Common Mistakes:**
- Disabling when you have setUp/tearDown methods- Not understanding the fixture conversion process---

### `transform_skip_decorators`

**Type:** `bool`
**Default:** `True`
**Importance:** Recommended

Whether to convert unittest skip decorators to pytest equivalents.

**CLI Flag:** `--transform-skip-decorators`

**Environment Variable:** `SPLURGE_TRANSFORM_SKIP_DECORATORS`

**Examples:**
- `true`- `false`**Common Mistakes:**
- Disabling when you have skip decorators- Not understanding pytest skip syntax differences---

### `transform_subtests`

**Type:** `bool`
**Default:** `True`
**Importance:** Optional

Whether to attempt subTest conversions to pytest parametrize.

**CLI Flag:** `--transform-subtests`

**Environment Variable:** `SPLURGE_TRANSFORM_SUBTESTS`

**Examples:**
- `true`- `false`**Related Fields:**
- `parametrize`**Common Mistakes:**
- Disabling when you have subTest usage- Not understanding subTest complexity can cause failures---

## Processing Options

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `cache_analysis_results` | `bool` | `True` | 🟢 optional | Whether to cache analysis results for improved performance. || `continue_on_error` | `bool` | `False` | 🟢 optional | Whether to continue processing other files when one file fails. || `max_concurrent_files` | `int` | `1` | 🟢 optional | Maximum number of files to process concurrently. |### `cache_analysis_results`

**Type:** `bool`
**Default:** `True`
**Importance:** Optional

Whether to cache analysis results for improved performance.

**CLI Flag:** `--cache-analysis-results`

**Environment Variable:** `SPLURGE_CACHE_ANALYSIS_RESULTS`

**Examples:**
- `true`- `false`**Common Mistakes:**
- Disabling when you have repeated runs on same files- Not understanding this improves performance for large codebases---

### `continue_on_error`

**Type:** `bool`
**Default:** `False`
**Importance:** Optional

Whether to continue processing other files when one file fails.

**CLI Flag:** `--continue-on-error`

**Environment Variable:** `SPLURGE_CONTINUE_ON_ERROR`

**Examples:**
- `true`- `false`**Related Fields:**
- `fail_fast`**Common Mistakes:**
- Disabling in development when you want to see all errors- Enabling in CI when you want fast failure feedback---

### `max_concurrent_files`

**Type:** `int`
**Default:** `1`
**Importance:** Optional

Maximum number of files to process concurrently.

**CLI Flag:** `--max-concurrent-files`

**Environment Variable:** `SPLURGE_MAX_CONCURRENT_FILES`

**Examples:**
- `1`- `4`- `8`**Constraints:**
- Must be between 1-50**Common Mistakes:**
- Setting too high causing resource exhaustion- Setting to 1 when you have many files to process---

## Advanced Options

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `create_source_map` | `bool` | `False` | 🟢 optional | Whether to create source mapping for debugging transformations. || `max_depth` | `int` | `7` | 🟢 optional | Maximum depth to traverse nested control flow structures. || `preserve_file_encoding` | `bool` | `True` | 🟢 optional | Whether to preserve original file encoding in output files. |### `create_source_map`

**Type:** `bool`
**Default:** `False`
**Importance:** Optional

Whether to create source mapping for debugging transformations.

**CLI Flag:** `--create-source-map`

**Environment Variable:** `SPLURGE_CREATE_SOURCE_MAP`

**Examples:**
- `true`- `false`**Common Mistakes:**
- Enabling in production causing unnecessary overhead- Not enabling when debugging transformation issues---

### `max_depth`

**Type:** `int`
**Default:** `7`
**Importance:** Optional

Maximum depth to traverse nested control flow structures.

**CLI Flag:** `--max-depth`

**Environment Variable:** `SPLURGE_MAX_DEPTH`

**Examples:**
- `7`- `5`- `10`**Constraints:**
- Must be between 3-15**Common Mistakes:**
- Setting too low causing incomplete transformations- Setting too high causing performance issues---

### `preserve_file_encoding`

**Type:** `bool`
**Default:** `True`
**Importance:** Optional

Whether to preserve original file encoding in output files.

**CLI Flag:** `--preserve-file-encoding`

**Environment Variable:** `SPLURGE_PRESERVE_FILE_ENCODING`

**Examples:**
- `true`- `false`**Common Mistakes:**
- Disabling when you have non-UTF-8 files- Not understanding encoding preservation implications---

## Test Method Patterns

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `test_method_prefixes` | `list[str]` | `['test', 'spec', ...` | 🔴 required | Prefixes that identify test methods for transformation. |### `test_method_prefixes`

**Type:** `list[str]`
**Default:** `['test', 'spec', 'should', 'it']`
**Importance:** Required

Prefixes that identify test methods for transformation.

**CLI Flag:** `--test-method-prefixes`

**Environment Variable:** `SPLURGE_TEST_METHOD_PREFIXES`

**Examples:**
- `['test']`- `['test', 'spec', 'should']`- `['test', 'it', 'describe']`**Constraints:**
- At least one prefix required**Common Mistakes:**
- Not including all your test method prefixes- Using prefixes that conflict with non-test methods---

## Parametrize Settings

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `parametrize` | `bool` | `True` | 🟢 optional | Whether to convert unittest subTests to pytest parametrize. || `parametrize_ids` | `bool` | `False` | 🟢 optional | Whether to add ids parameter to parametrize decorators. || `parametrize_type_hints` | `bool` | `False` | 🟢 optional | Whether to add type hints to parametrize parameters. |### `parametrize`

**Type:** `bool`
**Default:** `True`
**Importance:** Optional

Whether to convert unittest subTests to pytest parametrize.

**CLI Flag:** `--parametrize`

**Environment Variable:** `SPLURGE_PARAMETRIZE`

**Examples:**
- `true`- `false`**Related Fields:**
- `transform_subtests`- `parametrize_ids`- `parametrize_type_hints`**Common Mistakes:**
- Disabling when you want subTest conversion- Not understanding parametrize vs subTest differences---

### `parametrize_ids`

**Type:** `bool`
**Default:** `False`
**Importance:** Optional

Whether to add ids parameter to parametrize decorators.

**CLI Flag:** `--parametrize-ids`

**Environment Variable:** `SPLURGE_PARAMETRIZE_IDS`

**Examples:**
- `true`- `false`**Related Fields:**
- `parametrize`**Common Mistakes:**
- Enabling without understanding id generation- Not using ids for better test output readability---

### `parametrize_type_hints`

**Type:** `bool`
**Default:** `False`
**Importance:** Optional

Whether to add type hints to parametrize parameters.

**CLI Flag:** `--parametrize-type-hints`

**Environment Variable:** `SPLURGE_PARAMETRIZE_TYPE_HINTS`

**Examples:**
- `true`- `false`**Related Fields:**
- `parametrize`**Common Mistakes:**
- Enabling without having type information available- Not understanding type hint generation limitations---

## Degradation Settings

| Field | Type | Default | Importance | Description ||-------|------|---------|------------|-------------|| `degradation_tier` | `str` | `advanced` | 🟢 optional | Degradation tier determining fallback behavior (essential, advanced, experimental). || `degradation_enabled` | `bool` | `True` | 🟡 recommended | Whether to enable degradation for failed transformations. |### `degradation_enabled`

**Type:** `bool`
**Default:** `True`
**Importance:** Recommended

Whether to enable degradation for failed transformations.

**CLI Flag:** `--degradation-enabled`

**Environment Variable:** `SPLURGE_DEGRADATION_ENABLED`

**Examples:**
- `true`- `false`**Related Fields:**
- `degradation_tier`**Common Mistakes:**
- Disabling when you want robust transformation fallbacks- Not understanding degradation provides partial results---

### `degradation_tier`

**Type:** `str`
**Default:** `advanced`
**Importance:** Optional

Degradation tier determining fallback behavior (essential, advanced, experimental).

**CLI Flag:** `--degradation-tier`

**Environment Variable:** `SPLURGE_DEGRADATION_TIER`

**Examples:**
- `essential`- `advanced`- `experimental`**Constraints:**
- Must be one of: essential, advanced, experimental**Related Fields:**
- `degradation_enabled`- `dry_run`**Common Mistakes:**
- Using experimental without dry_run first- Not understanding tier differences in transformation quality---

