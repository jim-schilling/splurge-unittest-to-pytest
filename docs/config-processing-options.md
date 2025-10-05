# Processing Options Configuration

This document covers all configuration options in the processing options category.

### `cache_analysis_results`

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

