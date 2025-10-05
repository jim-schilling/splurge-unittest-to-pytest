# Transform Selection Configuration

This document covers all configuration options in the transform selection category.

### `transform_assertions`

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

