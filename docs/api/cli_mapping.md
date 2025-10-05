# CLI to Programmatic Mapping

This document maps Typer CLI commands to their programmatic equivalents.

- `generate-templates` -> `ConfigurationTemplateManager.load_templates()` and `ConfigurationTemplateManager.apply_template()`
- `configure` -> `InteractiveConfigBuilder` and `IntegratedConfigurationManager` for building and validating configuration programmatically
- `migrate` -> `main.migrate()` programmatic entrypoint
- `error-recovery` -> helpers under `splurge_unittest_to_pytest.error_recovery` (if present) that accept a file path and return suggested edits or a recovered AST

Quick examples

Programmatically generate templates:

```python
from splurge_unittest_to_pytest.config_validation import ConfigurationTemplateManager
mgr = ConfigurationTemplateManager(template_dir="./templates")
for name, tpl in mgr.load_templates().items():
    print(name)
    print(tpl.description)
```

Programmatically run configure (non-interactive):

```python
from splurge_unittest_to_pytest.config_validation import IntegratedConfigurationManager
from splurge_unittest_to_pytest.context import MigrationConfig

icm = IntegratedConfigurationManager()
cfg, warnings = icm.merge_config_sources(
    cli_flags={"dry_run": True},
    template_name=None,
    interactive_answers={}
)
```

CI integration example

```python
# Minimal script to run conversion in CI as part of a job
from splurge_unittest_to_pytest.main import migrate
from splurge_unittest_to_pytest.context import MigrationConfig

cfg = MigrationConfig(dry_run=False)
cfg.skip_backup = True
cfg.target_root = "./converted"

result = migrate(["tests/"], config=cfg)
if not result.is_success():
    # Fail the CI step
    raise SystemExit(1)
```

Plugin hooks and extension points

The library exposes a lightweight plugin hook system for three extension points:

- pre_process_file(source_path, context) -> optional modified_source
- post_process_ast(ast_tree, context) -> optional modified_ast
- report_event(event, context) -> None

Example plugin registration (simple function-based hooks):

```python
from splurge_unittest_to_pytest.plugins import register_hook

def my_preprocessor(source_path, context):
    # return None to indicate no change
    return None

register_hook("pre_process_file", my_preprocessor)
```

Run migration via API:

```python
from splurge_unittest_to_pytest.main import migrate
result = migrate(["test_sample.py"], config=cfg)
```

