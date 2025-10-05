# Parametrize Settings Configuration

This document covers all configuration options in the parametrize settings category.

### `parametrize`

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

