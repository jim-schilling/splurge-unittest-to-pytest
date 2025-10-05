# Degradation Settings Configuration

This document covers all configuration options in the degradation settings category.

### `degradation_enabled`

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

