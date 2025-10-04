# Import Handling Configuration

This document covers all configuration options in the import handling category.

### `format_output`

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

