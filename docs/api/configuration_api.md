# Configuration API

This document describes programmatic configuration structures and helpers.

## MigrationConfig / ValidatedMigrationConfig

- `MigrationConfig` is the user-facing configuration dataclass used by CLI and programmatic APIs.
- `ValidatedMigrationConfig` is the validated form (may use pydantic-like validation) that enforces cross-field constraints and normalized fields.

Common fields (examples):
- `dry_run: bool` — when True, generated code is returned in metadata instead of written to disk.
- `target_suffix: str` — suffix appended to converted file names (e.g., `_py` or `_pytest`).
- `target_extension: str` — file extension for target files (e.g., `.py`).
- `templates: List[str]` — template names to apply during conversion.

Construction examples:

```python
from splurge_unittest_to_pytest.context import MigrationConfig

cfg = MigrationConfig()
cfg.dry_run = True
cfg.target_suffix = "_converted"
cfg.target_extension = ".py"
```

Concrete `MigrationConfig` schema (example)

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MigrationConfig:
    dry_run: bool = False
    target_root: Optional[str] = None
    target_suffix: str = ""
    target_extension: str = ".py"
    backup_root: Optional[str] = None
    skip_backup: bool = False
    prefixes: List[str] = None
    templates: List[str] = None
    max_file_size_mb: int = 5
    use_case_analysis: bool = True
    suggestions: bool = True

    def __post_init__(self):
        if self.prefixes is None:
            self.prefixes = ["test"]
        if self.templates is None:
            self.templates = []
```

Template JSON/YAML shape

Configuration templates are simple mappings of configuration keys to values. A sample template file (YAML) looks like:

```yaml
name: ci_integration
description: "Optimized settings for CI runners: small file limits, no backups, quiet output."
settings:
  dry_run: false
  skip_backup: true
  target_suffix: "_pytest"
  prefixes:
    - test
    - spec
  max_file_size_mb: 1
```

When `ConfigurationTemplateManager` loads templates it returns a dict {name: TemplateMeta} where `TemplateMeta` contains `description` and `settings` that will be merged with a base `MigrationConfig`.

Validation notes:

- Constructing `ValidatedMigrationConfig` may run cross-field validators and raise an exception if fields conflict. When writing tests that need to avoid these validators, either:
  - Provide minimal valid values for dependent fields, or
  - Use simpler helper objects (e.g., SimpleNamespace) to test internal helper functions without constructing the validated model.

Helpers:

- `ConfigurationTemplateManager` — loads available templates from disk or packaged resources. Use `load_templates()` to discover templates and `apply_template(name, config)` to get a config merged with template defaults.
- `IntegratedConfigurationManager` — merges multiple configuration sources (CLI flags, templates, interactive answers) and provides a final validated config. It handles reporting warnings for ignored fields and validation errors.

Example: applying a template

```python
from splurge_unittest_to_pytest.config_validation import ConfigurationTemplateManager

mgr = ConfigurationTemplateManager(template_dir="./templates")
templates = mgr.load_templates()
cfg = mgr.apply_template(templates[0], MigrationConfig())
```

