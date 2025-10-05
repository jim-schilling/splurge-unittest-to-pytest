"""Example: configuration flow and template application

Demonstrates how to programmatically load templates, merge CLI flags, and run
`migrate()` in dry-run mode to inspect generated code without writing files.

Run:

    python examples/example_config_flow.py

"""

from pathlib import Path
from pprint import pprint

from splurge_unittest_to_pytest.config_validation import (
    ConfigurationTemplateManager,
    IntegratedConfigurationManager,
)

# MigrationConfig is not required in this example; the IntegratedConfigurationManager
# returns a fully merged configuration object.
from splurge_unittest_to_pytest.main import migrate


def main() -> None:
    # Load templates from the packaged templates folder (fallback to ./templates)
    template_dir = Path("./templates")
    tm = ConfigurationTemplateManager(template_dir=template_dir)

    templates = tm.load_templates()
    print("Available templates:")
    pprint(list(templates.keys()))

    # Build a base CLI-like flags dict
    cli_flags = {"dry_run": True, "skip_backup": True}

    icm = IntegratedConfigurationManager()

    # Merge CLI flags with a selected template if present
    selected = "ci_integration" if "ci_integration" in templates else None
    final_cfg, warnings = icm.merge_config_sources(cli_flags=cli_flags, template_name=selected, interactive_answers={})

    if warnings:
        print("Configuration warnings:")
        pprint(warnings)

    print("Final configuration:")
    pprint(final_cfg)

    # Run a dry-run migration for demonstration (no files are written when dry_run=True)
    result = migrate(["tests/test_example.py"], config=final_cfg)

    if result.is_success():
        print("Dry-run generated code mapping:")
        generated = result.metadata.get("generated_code", {}) if result.metadata else {}
        for path, src in generated.items():
            print("---", path)
            print(src[:400])
    else:
        print("Migration failed:")
        print(result.error)


if __name__ == "__main__":
    main()
