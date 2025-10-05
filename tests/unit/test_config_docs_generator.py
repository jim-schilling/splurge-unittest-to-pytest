"""Tests for configuration documentation generator."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from splurge_unittest_to_pytest.config_docs_generator import (
    ConfigurationDocumentationGenerator,
    generate_config_docs,
)
from splurge_unittest_to_pytest.config_metadata import get_categories, get_fields_by_category


class TestConfigurationDocumentationGenerator:
    """Test ConfigurationDocumentationGenerator class."""

    def test_initialization(self):
        """Test generator initialization."""
        generator = ConfigurationDocumentationGenerator()

        assert generator.metadata is not None
        assert len(generator.metadata) > 0

    def test_generate_markdown_docs(self, tmp_path):
        """Test generating markdown documentation."""
        generator = ConfigurationDocumentationGenerator()
        output_path = tmp_path / "config-docs.md"

        generator.generate_markdown_docs(output_path)

        # Check that main file was created
        assert output_path.exists()

        # Check that category files were created in the same directory as the output file
        categories = get_categories()
        for category in categories:
            category_file = output_path.parent / f"config-{category.lower().replace(' ', '-')}.md"
            assert category_file.exists()

        # Check content of main file
        content = output_path.read_text()
        assert "# Configuration Reference" in content
        assert "## Table of Contents" in content

        for category in categories:
            assert category in content

    def test_generate_html_docs(self, tmp_path):
        """Test generating HTML documentation."""
        generator = ConfigurationDocumentationGenerator()
        output_path = tmp_path / "config-docs.html"

        generator.generate_html_docs(output_path)

        assert output_path.exists()

        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "<title>Configuration Documentation</title>" in content

    def test_generate_main_reference(self):
        """Test generating main reference content."""
        generator = ConfigurationDocumentationGenerator()
        content = generator._generate_main_reference()

        assert "# Configuration Reference" in content
        assert "## Table of Contents" in content

        categories = get_categories()
        for category in categories:
            assert category in content

    def test_generate_category_section(self):
        """Test generating category section content."""
        generator = ConfigurationDocumentationGenerator()
        categories = get_categories()

        for category in categories:
            section = generator._generate_category_section(category)

            assert f"## {category}" in "".join(section)

            # Check table headers
            section_str = "".join(section)
            if get_fields_by_category(category):
                assert "| Field | Type | Default | Importance | Description |" in section_str
                assert "|-------|------|---------|------------|-------------|" in section_str

    def test_generate_field_details(self):
        """Test generating field details content."""
        generator = ConfigurationDocumentationGenerator()

        # Get a sample field
        fields = list(generator.metadata.values())
        if fields:
            field = fields[0]
            details = generator._generate_field_details(field)

            details_str = "".join(details)
            assert f"### `{field.name}`" in details_str
            assert f"**Type:** `{field.type}`" in details_str
            assert f"**Default:** `{field.default_value}`" in details_str
            assert field.description in details_str

            if field.cli_flag:
                assert f"**CLI Flag:** `{field.cli_flag}`" in details_str

            if field.environment_variable:
                assert f"**Environment Variable:** `{field.environment_variable}`" in details_str

    def test_generate_category_docs(self):
        """Test generating standalone category documentation."""
        generator = ConfigurationDocumentationGenerator()
        categories = get_categories()

        for category in categories:
            content = generator._generate_category_docs(category)

            assert f"# {category} Configuration" in content
            assert f"This document covers all configuration options in the {category.lower()} category." in content

    def test_validate_documentation_coverage(self):
        """Test documentation coverage validation."""
        generator = ConfigurationDocumentationGenerator()
        issues = generator.validate_documentation_coverage()

        # Should return a list
        assert isinstance(issues, list)

        # Check that issues are properly formatted
        for issue in issues:
            assert isinstance(issue, str)
            assert ":" in issue

    def test_validate_documentation_coverage_complete(self):
        """Test that documentation coverage is complete."""
        generator = ConfigurationDocumentationGenerator()
        issues = generator.validate_documentation_coverage()

        # In a well-maintained system, there should be no critical issues
        critical_issues = [issue for issue in issues if "Missing description" in issue]
        assert len(critical_issues) == 0, f"Fields missing descriptions: {critical_issues}"


class TestGenerateConfigDocsFunction:
    """Test the generate_config_docs function."""

    def test_generate_config_docs_markdown(self, tmp_path):
        """Test generate_config_docs with markdown format."""
        output_dir = tmp_path / "docs"

        generate_config_docs(output_dir, "markdown")

        assert (output_dir / "configuration-reference.md").exists()

        # Check that category files were created
        categories = get_categories()
        for category in categories:
            category_file = output_dir / f"config-{category.lower().replace(' ', '-')}.md"
            assert category_file.exists()

    def test_generate_config_docs_html(self, tmp_path):
        """Test generate_config_docs with HTML format."""
        output_dir = tmp_path / "docs"

        generate_config_docs(output_dir, "html")

        assert (output_dir / "configuration-reference.html").exists()
        assert (output_dir / "configuration-reference.md").exists()  # HTML generation also creates markdown

    def test_generate_config_docs_invalid_format(self, tmp_path):
        """Test generate_config_docs with invalid format."""
        output_dir = tmp_path / "docs"

        with pytest.raises(ValueError, match="Unsupported format"):
            generate_config_docs(output_dir, "invalid")

    @patch(
        "splurge_unittest_to_pytest.config_docs_generator.ConfigurationDocumentationGenerator.validate_documentation_coverage"
    )
    def test_generate_config_docs_with_issues(self, mock_validate, capsys):
        """Test generate_config_docs when validation issues exist."""
        mock_validate.return_value = ["field1: Missing description", "field2: Missing examples"]

        # The function should not raise SystemExit, just print issues and return
        generate_config_docs("dummy_dir", "markdown")

        captured = capsys.readouterr()
        assert "Documentation validation issues:" in captured.out
        assert "field1: Missing description" in captured.out
        assert "field2: Missing examples" in captured.out

    def test_generate_config_docs_creates_directory(self, tmp_path):
        """Test that generate_config_docs creates output directory if it doesn't exist."""
        output_dir = tmp_path / "new_docs" / "subdir"

        generate_config_docs(output_dir, "markdown")

        assert output_dir.exists()
        assert (output_dir / "configuration-reference.md").exists()


class TestDocumentationContent:
    """Test the actual content generated by the documentation generator."""

    def test_main_reference_structure(self):
        """Test that main reference has proper structure."""
        generator = ConfigurationDocumentationGenerator()
        content = generator._generate_main_reference()

        lines = content.split("\n")

        # Should start with title
        assert lines[0] == "# Configuration Reference"
        assert lines[1] == "This document provides comprehensive reference for all configuration options."
        assert lines[2] == "Auto-generated from the configuration metadata system."

        # Should have table of contents
        toc_index = None
        for i, line in enumerate(lines):
            if "## Table of Contents" in line:
                toc_index = i
                break

        assert toc_index is not None

        # Should have category sections
        categories = get_categories()
        for category in categories:
            assert f"## {category}" in content

    def test_category_section_has_table(self):
        """Test that category sections include proper tables."""
        generator = ConfigurationDocumentationGenerator()
        categories = get_categories()

        for category in categories:
            section = generator._generate_category_section(category)
            section_str = "".join(section)

            # Should have the category header
            assert f"## {category}" in section_str

            fields = get_fields_by_category(category)
            if fields:
                # Should have table headers
                assert "| Field | Type | Default | Importance | Description |" in section_str
                assert "|-------|------|---------|------------|-------------|" in section_str

    def test_field_details_comprehensive(self):
        """Test that field details are comprehensive."""
        generator = ConfigurationDocumentationGenerator()

        # Test with a field that has all optional attributes
        for field in generator.metadata.values():
            if field.cli_flag and field.environment_variable and field.examples and field.constraints:
                details = generator._generate_field_details(field)
                details_str = "".join(details)

                # Should include all sections
                assert f"**CLI Flag:** `{field.cli_flag}`" in details_str
                assert f"**Environment Variable:** `{field.environment_variable}`" in details_str
                assert "**Examples:**" in details_str
                assert "**Constraints:**" in details_str
                break

    def test_markdown_formatting(self):
        """Test that generated markdown has proper formatting."""
        generator = ConfigurationDocumentationGenerator()
        content = generator._generate_main_reference()

        # Should not have trailing whitespace
        lines = content.split("\n")
        for line in lines:
            assert not line.endswith(" "), f"Line has trailing whitespace: {repr(line)}"

        # Should have proper header hierarchy
        assert content.count("# ") >= 1  # At least one H1
        assert content.count("## ") >= 1  # At least one H2

    def test_html_basic_structure(self):
        """Test that generated HTML has basic structure."""
        generator = ConfigurationDocumentationGenerator()

        with patch("pathlib.Path.write_text") as mock_write:
            generator.generate_html_docs("dummy.html")

            # Check that write_text was called
            assert mock_write.called

            # Get the content that was written
            call_args = mock_write.call_args
            content = call_args[0][0]

            assert "<!DOCTYPE html>" in content
            assert "<html>" in content
            assert "<head>" in content
            assert "<body>" in content
            assert "</html>" in content
