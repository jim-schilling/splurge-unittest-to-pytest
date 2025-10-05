# Transformation Settings Configuration

This document covers all configuration options in the transformation settings category.

### `assert_almost_equal_places`

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

