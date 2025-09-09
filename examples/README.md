# Examples

This directory contains example scripts demonstrating various features of splurge-unittest-to-pytest.

## Available Examples

### `basic_usage.py`

Shows the most common use case - converting basic unittest code to pytest:

- Converting `unittest.TestCase` classes
- Removing `self.` prefixes from assertions
- Basic import cleanup

**To run:**
```bash
python examples/basic_usage.py
```

### `cli_usage.py`

Demonstrates command-line usage of the converter:

- Creating temporary test files
- Running the CLI tool with `--dry-run`
- Showing CLI output and options
- Cleaning up temporary files

**To run:**
```bash
python examples/cli_usage.py
```

### `demo_flexible_parameters.py`

Demonstrates the flexible parameter handling system for different method types:

- **Instance methods** with `self` parameter
- **Class methods** with `cls` parameter
- **Static methods** (no parameter removal)
- **Methods without conventional first parameters**

**To run:**
```bash
python examples/demo_flexible_parameters.py
```

This script shows how the converter intelligently handles different method types and removes parameters appropriately while preserving the method's functionality.

## Adding New Examples

When adding new example scripts:

1. Place them in this `examples/` directory
2. Include a shebang line (`#!/usr/bin/env python3`)
3. Add comprehensive docstrings
4. Update this README with the new example
5. Ensure the script can be run standalone with `python examples/script_name.py`
