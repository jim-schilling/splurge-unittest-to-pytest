# splurge-unittest-to-pytest Examples

This directory contains examples demonstrating how to use `splurge-unittest-to-pytest` both through the command-line interface (CLI) and programmatically via the API.

## CLI Example (`cli_basic.py`)

The CLI example demonstrates how to use the `splurge-unittest-to-pytest` command-line tool to migrate unittest test suites to pytest format.

### Features Demonstrated:
- **Basic migration**: Converting single unittest files
- **Directory migration**: Batch processing of multiple files
- **CLI commands**: `migrate`, `version`, `init-config`
- **Verbose output**: Detailed logging of the migration process
- **Real-time execution**: Shows actual migration results

### Usage:
```bash
# From the project root
python examples/cli_basic.py
```

## API Example (`api_basic.py`)

The API example demonstrates how to use the `splurge-unittest-to-pytest` library programmatically in your Python code.

### Features Demonstrated:
- **Single file migration**: Converting individual unittest files
- **Directory migration**: Batch processing using the API
- **Configuration options**: Customizing migration settings
- **Error handling**: Proper exception handling for edge cases
- **Result processing**: Working with migration results

### Key Classes Used:
- `MigrationOrchestrator`: Main orchestrator for migrations
- `MigrationConfig`: Configuration settings for migrations
- `Result`: Functional error handling with success/failure states

### Usage:
```bash
# From the project root
python examples/api_basic.py
```

## What You'll Learn

### CLI Usage:
- How to migrate single files or entire directories
- Available command-line options and flags
- How to get version information
- How to initialize configuration files

### API Usage:
- How to integrate the migration tool into your own applications
- How to configure migration behavior programmatically
- How to handle migration results and errors
- How to process multiple files in batch operations

## Real-World Applications

### CLI Examples:
- **CI/CD Integration**: Use in automated build pipelines
- **Code Migration Scripts**: Batch migrate entire test suites
- **Developer Workflows**: Quick conversion during development

### API Examples:
- **IDE Plugins**: Build unittest-to-pytest conversion features
- **Code Analysis Tools**: Integrate migration into code quality checks
- **Custom Scripts**: Automate test suite modernization
- **Build Tools**: Add migration to existing build processes

## Running the Examples

Both examples are self-contained and will:
1. Create temporary unittest files to demonstrate the migration
2. Show the migration process with detailed logging
3. Display the generated pytest code
4. Clean up temporary files automatically

The examples are designed to be safe to run multiple times and demonstrate both success and error scenarios.
