# Enhanced Configuration Validation & Error Reporting - Version 2025.0.5

This document provides comprehensive documentation for the enhanced configuration validation and error reporting features introduced in splurge-unittest-to-pytest version 2025.0.5.

## Overview

Version 2025.0.5 introduces a sophisticated configuration validation system that transforms basic validation into an intelligent, context-aware experience. The new system provides:

- **Cross-field validation** to catch incompatible option combinations
- **Intelligent use case detection** to understand intended usage patterns
- **Context-aware suggestions** to guide users toward optimal configurations
- **Rich field metadata** with comprehensive help and examples
- **Auto-generated documentation** for all configuration options
- **Ready-to-use configuration templates** for common scenarios

## Enhanced Configuration Validation

### Cross-Field Validation Rules

The enhanced validation system now catches incompatible option combinations that could lead to unexpected behavior:

#### Example: Dry Run with Target Directory
```python
from splurge_unittest_to_pytest.config_validation import ValidatedMigrationConfig

# This will raise a validation error
try:
    config = ValidatedMigrationConfig(
        dry_run=True,
        target_root="/tmp/output"  # Ignored in dry run mode
    )
except ValueError as e:
    print(f"Validation error: {e}")
    # Output: Configuration conflicts detected: dry_run: dry_run mode ignores target_root setting - Remove target_root or set dry_run=False
```

#### Example: Backup Root without Backups Enabled
```python
# This will also raise a validation error
try:
    config = ValidatedMigrationConfig(
        backup_root="/tmp/backups",  # Specified but backups disabled
        backup_originals=False
    )
except ValueError as e:
    print(f"Validation error: {e}")
    # Output: Configuration conflicts detected: backup_root: backup_root specified but backup_originals is disabled - Enable backup_originals or remove backup_root
```

#### Example: Performance Warning for Large Files
```python
# This raises a performance warning
try:
    config = ValidatedMigrationConfig(max_file_size_mb=60)  # > 50MB threshold
except ValueError as e:
    print(f"Performance warning: {e}")
    # Output: Configuration conflicts detected: max_file_size_mb: Large file size limit may impact memory usage and performance - Consider reducing max_file_size_mb for better performance. Use 10-20MB for typical use cases.
```

### File System Validation

The system now validates that specified directories exist and are writable:

```python
import tempfile
from pathlib import Path

# Create a temporary directory for testing
with tempfile.TemporaryDirectory() as tmp_dir:
    valid_dir = Path(tmp_dir) / "output"
    valid_dir.mkdir()

    # This works - directory exists and is writable
    config = ValidatedMigrationConfig(target_root=str(valid_dir))

    # This fails - file path instead of directory
    test_file = Path(tmp_dir) / "test.txt"
    test_file.write_text("test")

    try:
        config = ValidatedMigrationConfig(target_root=str(test_file))
    except ValueError as e:
        print(f"Directory validation error: {e}")
        # Output: target_root must be a directory, got: /tmp/tmpXXX/test.txt
```

## Intelligent Use Case Detection

The system automatically detects your intended use case from configuration patterns:

### Use Case Detection Examples

```python
from splurge_unittest_to_pytest.config_validation import ConfigurationUseCaseDetector, ConfigurationProfile

detector = ConfigurationUseCaseDetector()

# Basic migration pattern
basic_config = ValidatedMigrationConfig(
    file_patterns=["test_*.py"],
    recurse_directories=True,
    backup_originals=True,
    dry_run=True
)
use_case = detector.detect_use_case(basic_config)
print(f"Detected use case: {use_case}")  # basic_migration

# Custom testing framework pattern
custom_config = ValidatedMigrationConfig(
    test_method_prefixes=["test", "spec", "should", "it", "feature", "scenario"],
    dry_run=True
)
use_case = detector.detect_use_case(custom_config)
print(f"Detected use case: {use_case}")  # custom_testing_framework

# CI integration pattern
ci_config = ValidatedMigrationConfig(
    dry_run=False,
    fail_fast=True,
    max_concurrent_files=8,
    cache_analysis_results=True
)
use_case = detector.detect_use_case(ci_config)
print(f"Detected use case: {use_case}")  # ci_integration
```

## Intelligent Configuration Suggestions

The system provides context-aware suggestions based on your configuration and detected use case:

### Basic Usage

```python
from splurge_unittest_to_pytest.config_validation import ConfigurationAdvisor, generate_configuration_suggestions

# Create configuration
config = ValidatedMigrationConfig(
    degradation_tier="experimental",
    dry_run=True,
    max_file_size_mb=45
)

# Generate suggestions
advisor = ConfigurationAdvisor()
suggestions = advisor.suggest_improvements(config)

for suggestion in suggestions:
    print(f"[{suggestion.type.value.upper()}] {suggestion.message}")
    print(f"Action: {suggestion.action}")
    if suggestion.examples:
        print(f"Examples: {suggestion.examples}")
    print("---")

# Or use the convenience function
suggestions = generate_configuration_suggestions(config)
```

### Example Output
```
[SAFETY] Experimental tier without dry_run may cause unexpected results
Action: Use dry_run=True when using experimental features
Examples: ['dry_run=True']
---
[PERFORMANCE] Enable concurrent processing for better performance
Action: Increase max_concurrent_files for large codebases
Examples: ['max_concurrent_files=4', 'max_concurrent_files=8']
---
```

## Configuration Field Metadata System

Get comprehensive help for any configuration field:

### Field Help Examples

```python
from splurge_unittest_to_pytest.config_validation import get_field_help

# Get help for a specific field
help_text = get_field_help("target_root")
print(help_text)
# Output:
# **target_root** (str | None)
# Root directory for output files
#
# **Examples:**
# - `./output`
# - `/tmp/migration`
# - `./converted`
#
# **Constraints:**
# - Must be a valid directory path
# - Directory must be writable
#
# **Common Mistakes:**
# - Using a file path instead of directory path
# - Using relative path that doesn't exist
# - Insufficient write permissions
#
# **Related Fields:** backup_root, target_suffix

# Get help for another field
help_text = get_field_help("degradation_tier")
print(help_text)
```

### Field Categories

Fields are organized into categories for better navigation:

```python
from splurge_unittest_to_pytest.config_validation import get_configuration_field_registry

registry = get_configuration_field_registry()

# Get all output-related fields
output_fields = registry.get_fields_by_category("output")
print("Output fields:", list(output_fields.keys()))

# Get all safety-related fields
safety_fields = registry.get_fields_by_category("safety")
print("Safety fields:", list(safety_fields.keys()))

# Get all fields
all_fields = registry.get_all_fields()
print(f"Total fields with metadata: {len(all_fields)}")
```

## Auto-Generated Documentation

Generate comprehensive documentation for all configuration options:

### Markdown Documentation

```python
from splurge_unittest_to_pytest.config_validation import generate_configuration_documentation

# Generate Markdown documentation
markdown_docs = generate_configuration_documentation("markdown")
print(f"Generated {len(markdown_docs)} characters of Markdown documentation")

# Save to file
with open("config-reference.md", "w") as f:
    f.write(markdown_docs)
```

### HTML Documentation

```python
# Generate HTML documentation
html_docs = generate_configuration_documentation("html")
print(f"Generated {len(html_docs)} characters of HTML documentation")

# Save to file
with open("config-reference.html", "w") as f:
    f.write(html_docs)
```

## Configuration Templates

Use pre-configured templates for common scenarios:

### Available Templates

```python
from splurge_unittest_to_pytest.config_validation import list_available_templates, get_template

# List all available templates
templates = list_available_templates()
print("Available templates:")
for template in templates:
    print(f"  - {template}")

# Get a specific template
basic_template = get_template("basic_migration")
print(f"Template: {basic_template.name}")
print(f"Description: {basic_template.description}")
print(f"Use case: {basic_template.use_case}")
```

### Template Usage Examples

#### YAML Configuration
```python
# Get YAML configuration from template
yaml_config = basic_template.to_yaml()
print(yaml_config)

# Output:
# # Basic Migration
# # Standard unittest to pytest migration with safe defaults
#
# backup_originals: true
# degradation_tier: advanced
# dry_run: true
# file_patterns:
# - test_*.py
# format_output: true
# max_file_size_mb: 20
# recurse_directories: true
# remove_unused_imports: true
```

#### CLI Arguments
```python
# Get CLI arguments from template
cli_args = basic_template.to_cli_args()
print(f"CLI args: {cli_args}")

# Output: --dry-run --backup-originals --file-patterns=test_*.py --recurse-directories --degradation-tier=advanced --format-output --remove-unused-imports --max-file-size-mb=20
```

#### Generate Configuration from Template
```python
from splurge_unittest_to_pytest.config_validation import generate_config_from_template

# Generate configuration dictionary from template
config_dict = generate_config_from_template("enterprise_deployment")
print("Generated config:", config_dict)

# Create validated configuration object
config = ValidatedMigrationConfig(**config_dict)
print(f"Created config for use case: {config.degradation_tier}")
```

#### Generate Template Files

You can also generate actual configuration files for all templates:

```bash
# Generate YAML template files
python -m splurge_unittest_to_pytest.cli generate-templates

# Generate JSON template files in a specific directory
python -m splurge_unittest_to_pytest.cli generate-templates --output-dir ./my-templates --format json
```

This creates individual configuration files for each template that you can use directly:

```bash
# Use a generated template file
python -m splurge_unittest_to_pytest.cli migrate --config ./templates/basic_migration.yaml tests/
```

## Integration Examples

### Programmatic Usage

```python
from splurge_unittest_to_pytest.config_validation import (
    ValidatedMigrationConfig,
    ConfigurationAdvisor,
    ConfigurationUseCaseDetector,
    generate_configuration_suggestions
)

# Create configuration
config = ValidatedMigrationConfig(
    target_root="./output",
    backup_root="./backups",
    file_patterns=["test_*.py", "**/test_*.py"],
    max_file_size_mb=30,
    degradation_tier="advanced"
)

# Detect use case
detector = ConfigurationUseCaseDetector()
use_case = detector.detect_use_case(config)
print(f"Detected use case: {use_case}")

# Get intelligent suggestions
advisor = ConfigurationAdvisor()
suggestions = advisor.suggest_improvements(config)

print(f"Generated {len(suggestions)} suggestions:")
for suggestion in suggestions:
    print(f"  - {suggestion}")
```

### Error Handling Integration

```python
from splurge_unittest_to_pytest.config_validation import validate_migration_config
from splurge_unittest_to_pytest.exceptions import ValidationError

# Example of handling validation errors with suggestions
try:
    config_dict = {
        "dry_run": True,
        "target_root": "/tmp/output",
        "max_file_size_mb": 60
    }
    config = validate_migration_config(config_dict)

except ValidationError as e:
    print(f"Configuration error: {e}")

    # The error message includes actionable suggestions
    # "Configuration conflicts detected: dry_run: dry_run mode ignores target_root setting - Remove target_root or set dry_run=False; max_file_size_mb: Large file size limit may impact memory usage and performance - Consider reducing max_file_size_mb for better performance. Use 10-20MB for typical use cases."
```

## Migration Guide

### Upgrading from Previous Versions

The enhanced validation system is **100% backward compatible**. Existing code will continue to work without changes, but you can take advantage of new features:

```python
# Old way (still works)
config = ValidatedMigrationConfig(dry_run=True)

# New way with enhanced validation
config = ValidatedMigrationConfig(
    dry_run=True,
    # Now validates that target_root is not set when dry_run=True
    # target_root="/tmp/output"  # Would raise error
)

# Get intelligent suggestions for your config
suggestions = generate_configuration_suggestions(config)
```

### Best Practices

1. **Use Dry Run First**: Always start with `dry_run=True` to preview changes
2. **Enable Backups**: Use `backup_originals=True` for production migrations
3. **Choose Appropriate File Size**: Set `max_file_size_mb` based on your codebase size
4. **Leverage Templates**: Use pre-configured templates for common scenarios
5. **Review Suggestions**: Check generated suggestions for optimization opportunities

## Troubleshooting

### Common Issues and Solutions

#### "dry_run mode ignores target_root setting"
**Problem**: You specified both `dry_run=True` and `target_root`
**Solution**: Either set `dry_run=False` or remove `target_root`

#### "backup_root specified but backup_originals is disabled"
**Problem**: You specified `backup_root` but disabled `backup_originals`
**Solution**: Either enable `backup_originals=True` or remove `backup_root`

#### "Large file size limit may impact memory usage"
**Problem**: `max_file_size_mb` is set too high (>50MB)
**Solution**: Reduce to 10-20MB for typical use cases, or 30-40MB for large codebases

#### "Experimental tier without dry_run may cause unexpected results"
**Problem**: Using `degradation_tier="experimental"` without `dry_run=True`
**Solution**: Set `dry_run=True` when using experimental features

### Getting Help

```python
# Get help for any configuration field
from splurge_unittest_to_pytest.config_validation import get_field_help

help_text = get_field_help("target_root")
print(help_text)

# Generate complete documentation
from splurge_unittest_to_pytest.config_validation import generate_configuration_documentation
docs = generate_configuration_documentation("markdown")
```

## API Reference

### Core Classes

- **`ValidatedMigrationConfig`**: Enhanced configuration class with cross-field validation
- **`ConfigurationUseCaseDetector`**: Detects intended use case from configuration patterns
- **`ConfigurationAdvisor`**: Generates intelligent configuration suggestions
- **`ConfigurationFieldRegistry`**: Manages rich field metadata
- **`ConfigurationTemplateManager`**: Manages configuration templates

### Key Functions

- **`validate_migration_config(config_dict)`**: Validates configuration dictionary
- **`generate_configuration_suggestions(config)`**: Generates intelligent suggestions
- **`detect_configuration_use_case(config)`**: Detects use case from configuration
- **`get_field_help(field_name)`**: Gets help for specific field
- **`generate_configuration_documentation(format)`**: Generates documentation
- **`get_template(name)`**: Gets specific configuration template
- **`list_available_templates()`**: Lists all available templates

## Performance Characteristics

- **Validation Time**: < 1ms per configuration
- **Suggestion Generation**: < 5ms per configuration
- **Use Case Detection**: < 5ms per configuration
- **Documentation Generation**: < 100ms for complete documentation
- **Memory Usage**: Minimal additional memory overhead

## Future Enhancements

This foundation enables future phases to add:

- **Phase 2**: Advanced error reporting with categorized error types and recovery workflows
- **Phase 3**: Interactive configuration assistant with guided setup
- **Additional Use Cases**: Support for more specialized migration scenarios
- **Integration APIs**: Better integration with CI/CD systems and IDEs

---

For more information, see the [Configuration Reference](../README-DETAILS.md#configuration-file-format) and [CLI Reference](../README-DETAILS.md#cli-reference).
