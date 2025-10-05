# End-to-End API Workflow

This page shows a complete programmatic conversion workflow: analyze a project, build a configuration, validate it, and run the migration.

1. Analyze the project

```python
from splurge_unittest_to_pytest.config_validation import ProjectAnalyzer
from pathlib import Path

proj = ProjectAnalyzer(Path("./my_project"))
report = proj.analyze()
print("Detected frameworks:", report.frameworks)
```

2. Build a base configuration

```python
from splurge_unittest_to_pytest.context import MigrationConfig
cfg = MigrationConfig()
cfg.dry_run = True
cfg.target_suffix = "_pytest"
```

3. Merge and validate configuration

```python
from splurge_unittest_to_pytest.config_validation import IntegratedConfigurationManager
icm = IntegratedConfigurationManager()
final_cfg, warnings = icm.merge_config_sources(
    cli_flags={"dry_run": True},
    template_name=None,
    interactive_answers={},
)
if warnings:
    for w in warnings:
        print("Warning:", w)

Applying a template programmatically

```python
from splurge_unittest_to_pytest.config_validation import ConfigurationTemplateManager

tm = ConfigurationTemplateManager(template_dir="./templates")
templates = tm.load_templates()
tpl = templates.get("ci_integration")
if tpl:
    final_cfg = tm.apply_template(tpl, final_cfg)
```

Handling dry-run output

When `dry_run=True` the `Result.metadata` may contain a `generated_code` mapping. Use that mapping to inspect or assert expected transformations in automated tests.

```python
if result.is_success():
    gen = result.metadata.get("generated_code", {}) if result.metadata else {}
    for target, code in gen.items():
        # e.g. assert certain strings for CI checks
        assert "import pytest" in code
```

Error handling examples

```python
result = migrate(["tests/test_example.py"], config=final_cfg)
if not result.is_success():
    # result.error may be a ValidationError, MigrationError or a list of per-file errors
    print("Migration failed:", result.error)
    # For CI you may want to fail-fast:
    raise SystemExit(1)
```
```

4. Run migration

```python
from splurge_unittest_to_pytest.main import migrate
result = migrate(["tests/test_example.py"], config=final_cfg)
if result.is_success():
    print("Converted:", result.data)
    generated = result.metadata.get("generated_code", {}) if result.metadata else {}
    for p, src in generated.items():
        print(p)
        print(src)
else:
    print("Migration error:", result.error)
```

Notes and tips

- Use `dry_run=True` while crafting configuration to view generated code without writing files.
- If `IntegratedConfigurationManager` raises validation errors, inspect the returned error details to adjust conflicting fields.
- For automated scripts, wrap `migrate()` calls in try/except and handle `Result.failure` cases accordingly.

