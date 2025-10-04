# Configuration Templates

This directory contains pre-configured YAML templates for common unittest to pytest migration scenarios. Each template is designed for specific use cases and includes optimized settings.

## Available Templates

### `basic-migration.yaml`
**Purpose**: Minimal configuration for simple file-to-file migrations
**Use Case**: Converting a single test file with standard unittest patterns
**Key Features**:
- Single file input/output
- Essential migration options enabled
- Conservative error handling

### `comprehensive-migration.yaml`
**Purpose**: Full-featured configuration for complex migration scenarios
**Use Case**: Large-scale migrations requiring all available features
**Key Features**:
- All migration options enabled
- Advanced code quality features
- Comprehensive error handling and recovery
- Performance optimizations

### `batch-processing.yaml`
**Purpose**: Optimized for processing multiple test files
**Use Case**: Migrating entire test directories or codebases
**Key Features**:
- Glob pattern support for multiple files
- Parallel processing with configurable workers
- File filtering and exclusion patterns
- Batch-specific error handling

### `ci-cd-integration.yaml`
**Purpose**: Designed for automated migration in CI/CD pipelines
**Use Case**: Integrating migration into build/deployment workflows
**Key Features**:
- Environment variable support
- CI-specific timeouts and constraints
- Quality gates and test validation
- Artifact preservation and reporting

### `advanced-analysis.yaml`
**Purpose**: Comprehensive analysis and detailed reporting
**Use Case**: Understanding codebase complexity before migration
**Key Features**:
- Static analysis and code smell detection
- Complexity analysis and test coverage checking
- Detailed reporting in multiple formats
- Migration effort estimation

### `minimal.yaml`
**Purpose**: Bare minimum configuration for quick operations
**Use Case**: Fast, one-off migrations with minimal setup
**Key Features**:
- Only essential settings included
- Minimal logging and error handling
- Quick execution focus

## Usage

### Using Templates with CLI

```bash
# Use a template as a starting point
python -m splurge_unittest_to_pytest.cli --config examples/config-templates/basic-migration.yaml

# Override template settings via command line
python -m splurge_unittest_to_pytest.cli --config examples/config-templates/basic-migration.yaml --input-file "my_tests/" --verbose

# Use environment variables with templates
INPUT_PATH="tests/" OUTPUT_PATH="converted/" python -m splurge_unittest_to_pytest.cli --config examples/config-templates/ci-cd-integration.yaml
```

### Customizing Templates

1. Copy a template to your project directory
2. Modify settings according to your needs
3. Use the customized configuration with the CLI

```bash
cp examples/config-templates/comprehensive-migration.yaml my-project-config.yaml
# Edit my-project-config.yaml as needed
python -m splurge_unittest_to_pytest.cli --config my-project-config.yaml
```

## Template Structure

All templates follow the same YAML structure:

```yaml
# Input/Output Configuration
input_file: "path/to/input"
output_file: "path/to/output"

# Migration Options
migrate_assertions: true/false
migrate_setup_teardown: true/false
# ... other migration options

# Advanced Features
enable_static_analysis: true/false
# ... other advanced options

# Logging and Error Handling
log_level: "INFO"
strict_mode: false
# ... other settings
```

## Environment Variables

Templates support environment variable substitution using `${VARIABLE_NAME}` syntax:

- `INPUT_PATH`: Input file/directory path
- `OUTPUT_PATH`: Output file/directory path
- `LOG_LEVEL`: Logging verbosity level
- `SLACK_WEBHOOK`: Slack notification webhook URL
- `EMAIL_RECIPIENTS`: Email addresses for notifications
- `JIRA_PROJECT`: JIRA project key for issue tracking

## Best Practices

1. **Start Simple**: Begin with `basic-migration.yaml` for initial testing
2. **Scale Up**: Move to `comprehensive-migration.yaml` for production migrations
3. **Batch Processing**: Use `batch-processing.yaml` for multiple files
4. **CI/CD Integration**: Use `ci-cd-integration.yaml` for automated workflows
5. **Analysis First**: Run `advanced-analysis.yaml` to understand complexity before migrating
6. **Customize**: Copy and modify templates for project-specific needs

## Validation

All templates are validated against the configuration schema. Use the CLI validation:

```bash
python -m splurge_unittest_to_pytest.cli --validate-config examples/config-templates/basic-migration.yaml
```