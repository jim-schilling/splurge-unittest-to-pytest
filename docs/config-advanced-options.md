# Advanced Options Configuration

This document covers all configuration options in the advanced options category.

### `create_source_map`

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

