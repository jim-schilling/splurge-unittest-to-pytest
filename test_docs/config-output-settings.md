# Output Settings Configuration

This document covers all configuration options in the output settings category.

### `backup_originals`

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

