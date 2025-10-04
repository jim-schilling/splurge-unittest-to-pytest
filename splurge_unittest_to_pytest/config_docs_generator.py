"""Configuration documentation generator.

This module provides functionality to auto-generate comprehensive configuration
documentation from the metadata system.
"""

from __future__ import annotations

from pathlib import Path

from .config_metadata import (
    ConfigurationField,
    get_all_field_metadata,
    get_categories,
    get_fields_by_category,
)


class ConfigurationDocumentationGenerator:
    """Generates comprehensive configuration documentation."""

    def __init__(self):
        self.metadata = get_all_field_metadata()

    def generate_markdown_docs(self, output_path: str | Path) -> None:
        """Generate comprehensive Markdown documentation."""
        output_path = Path(output_path)

        # Generate main configuration reference
        content = self._generate_main_reference()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        # Generate category-specific docs
        for category in get_categories():
            category_content = self._generate_category_docs(category)
            category_path = output_path.parent / f"config-{category.lower().replace(' ', '-')}.md"
            category_path.write_text(category_content, encoding="utf-8")

    def generate_html_docs(self, output_path: str | Path) -> None:
        """Generate HTML documentation."""
        # For now, just generate Markdown and note HTML generation would need additional tooling
        markdown_path = Path(output_path).with_suffix(".md")
        self.generate_markdown_docs(markdown_path)

        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Configuration Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .field { margin-bottom: 30px; border: 1px solid #ddd; padding: 20px; }
        .required { border-left: 4px solid #d32f2f; }
        .recommended { border-left: 4px solid #f57c00; }
        .optional { border-left: 4px solid #388e3c; }
        .examples { background: #f5f5f5; padding: 10px; margin: 10px 0; }
        .constraints { color: #666; font-style: italic; }
        .cli-flag { font-family: monospace; background: #e3f2fd; padding: 2px 4px; }
        .env-var { font-family: monospace; background: #f3e5f5; padding: 2px 4px; }
    </style>
</head>
<body>
    <h1>Configuration Reference</h1>
    <p>This documentation is auto-generated from the configuration metadata system.</p>
    <p>For the latest version, see the Markdown documentation.</p>
</body>
</html>"""
        Path(output_path).write_text(html_content, encoding="utf-8")

    def _generate_main_reference(self) -> str:
        """Generate the main configuration reference document."""
        lines = [
            "# Configuration Reference\n",
            "This document provides comprehensive reference for all configuration options.\n",
            "Auto-generated from the configuration metadata system.\n\n",
            "## Table of Contents\n\n",
        ]

        # Add table of contents
        for category in get_categories():
            anchor = category.lower().replace(" ", "-")
            lines.append(f"- [{category}](#{anchor})\n")
        lines.append("\n")

        # Add each category section
        for category in get_categories():
            lines.extend(self._generate_category_section(category))

        return "".join(lines)

    def _generate_category_section(self, category: str) -> list[str]:
        """Generate a section for a specific category."""
        lines = [f"## {category}\n\n"]

        fields = get_fields_by_category(category)
        if not fields:
            lines.append("No fields in this category.\n\n")
            return lines

        # Add field overview table
        lines.extend(
            [
                "| Field | Type | Default | Importance | Description |",
                "|-------|------|---------|------------|-------------|",
            ]
        )

        for field in sorted(fields, key=lambda f: (f.importance == "required", f.importance == "recommended", f.name)):
            importance_icon = {"required": "🔴", "recommended": "🟡", "optional": "🟢"}.get(field.importance, "⚪")

            default_str = str(field.default_value)
            if len(default_str) > 20:
                default_str = default_str[:17] + "..."

            lines.append(
                f"| `{field.name}` | `{field.type}` | `{default_str}` | {importance_icon} {field.importance} | {field.description} |"
            )

        lines.append("")  # Empty line after table

        # Add detailed field documentation
        for field in sorted(fields, key=lambda f: f.name):
            lines.extend(self._generate_field_details(field))

        return lines

    def _generate_field_details(self, field: ConfigurationField) -> list[str]:
        """Generate detailed documentation for a single field."""
        lines = [
            f"### `{field.name}`\n\n",
            f"**Type:** `{field.type}`\n",
            f"**Default:** `{field.default_value}`\n",
            f"**Importance:** {field.importance.title()}\n\n",
            f"{field.description}\n\n",
        ]

        if field.cli_flag:
            lines.append(f"**CLI Flag:** `{field.cli_flag}`\n\n")

        if field.environment_variable:
            lines.append(f"**Environment Variable:** `{field.environment_variable}`\n\n")

        if field.examples:
            lines.append("**Examples:**\n")
            for example in field.examples:
                lines.append(f"- `{example}`")
            lines.append("")

        if field.constraints:
            lines.append("**Constraints:**\n")
            for constraint in field.constraints:
                lines.append(f"- {constraint}")
            lines.append("")

        if field.related_fields:
            lines.append("**Related Fields:**\n")
            for related in field.related_fields:
                lines.append(f"- `{related}`")
            lines.append("")

        if field.common_mistakes:
            lines.append("**Common Mistakes:**\n")
            for mistake in field.common_mistakes:
                lines.append(f"- {mistake}")
            lines.append("")

        lines.append("---\n\n")
        return lines

    def _generate_category_docs(self, category: str) -> str:
        """Generate standalone documentation for a category."""
        lines = [
            f"# {category} Configuration\n\n",
            f"This document covers all configuration options in the {category.lower()} category.\n\n",
        ]

        fields = get_fields_by_category(category)
        for field in sorted(fields, key=lambda f: f.name):
            lines.extend(self._generate_field_details(field))

        return "".join(lines)

    def validate_documentation_coverage(self) -> list[str]:
        """Validate that all fields have complete documentation."""
        issues = []

        for name, field in self.metadata.items():
            if not field.description:
                issues.append(f"{name}: Missing description")
            if not field.examples:
                issues.append(f"{name}: Missing examples")
            if field.importance not in ["required", "recommended", "optional"]:
                issues.append(f"{name}: Invalid importance level '{field.importance}'")

        return issues


def generate_config_docs(output_dir: str | Path = "docs", format: str = "markdown") -> None:
    """Generate configuration documentation.

    Args:
        output_dir: Directory to write documentation files
        format: Output format ('markdown' or 'html')
    """
    generator = ConfigurationDocumentationGenerator()

    # Validate coverage first
    issues = generator.validate_documentation_coverage()
    if issues:
        print("Documentation validation issues:")
        for issue in issues:
            print(f"  - {issue}")
        print("Please fix these issues before generating documentation.")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if format == "markdown":
        main_path = output_dir / "configuration-reference.md"
        generator.generate_markdown_docs(main_path)
        print(f"Generated Markdown documentation: {main_path}")
    elif format == "html":
        main_path = output_dir / "configuration-reference.html"
        generator.generate_html_docs(main_path)
        print(f"Generated HTML documentation: {main_path}")
    else:
        raise ValueError(f"Unsupported format: {format}")


if __name__ == "__main__":
    # Generate documentation when run directly
    generate_config_docs()
