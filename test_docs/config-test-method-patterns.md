# Test Method Patterns Configuration

This document covers all configuration options in the test method patterns category.

### `test_method_prefixes`

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

