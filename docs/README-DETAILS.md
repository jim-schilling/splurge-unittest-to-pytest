# Project Documentation Index

## Overview
This directory contains comprehensive documentation for the unittest-to-pytest migration tool, a production-ready system for automatically converting Python unittest test suites to pytest format while preserving code quality and test behavior.

## Document Structure

### 📋 Planning Documents
- **[Project Plan](project_plan.md)** - Complete project roadmap with phases, milestones, risk assessment, and success criteria
- **[Implementation Roadmap](implementation_roadmap.md)** - Detailed week-by-week implementation guide with concrete tasks and priorities

### 🏗️ Architecture Documents  
- **[Technical Specification](technical_specification.md)** - Comprehensive technical architecture, data models, and implementation details
- **[Architecture Diagrams](architecture_diagrams.md)** - Visual system architecture, data flows, and component interactions
- **[Project Structure](project_structure.md)** - Detailed source code organization and module dependencies

### ⚙️ Configuration
- **[unittest-to-pytest.yaml](../unittest-to-pytest.yaml)** - Complete configuration file example with all available options

## Quick Start Guide

### For Project Managers
1. Start with [Project Plan](project_plan.md) for timeline and resource requirements
2. Review [Implementation Roadmap](implementation_roadmap.md) for detailed task breakdown
3. Check milestones and success criteria for project tracking

### For Architects  
1. Read [Technical Specification](technical_specification.md) for system design
2. Study [Architecture Diagrams](architecture_diagrams.md) for visual understanding
3. Review [Project Structure](project_structure.md) for code organization

### For Developers
1. Begin with [Implementation Roadmap](implementation_roadmap.md) for task priorities
2. Reference [Technical Specification](technical_specification.md) for implementation details
3. Use [Project Structure](project_structure.md) for code navigation

## Key Architecture Principles

### Functional Pipeline Design
- **Jobs** → **Tasks** → **Steps** hierarchy with single responsibilities
- Pure functions with no side effects throughout the pipeline
- Immutable data structures (PipelineContext, Result containers)
- Deterministic transformations for reliable outputs

### Event-Driven Observability
- EventBus for pipeline execution monitoring
- Subscribers for logging, progress reporting, and analytics
- Non-intrusive observation without coupling pipeline logic

### Intermediate Representation
- Language-agnostic semantic model of test structure
- Separation of parsing concerns from generation concerns
- Enables validation and optimization between transformation phases

### Error-Safe Processing
- Comprehensive Result[T] containers with error propagation
- Graceful degradation with detailed error reporting
- Recovery strategies for different error categories

## Technology Stack

### Core Dependencies
- **libcst**: High-fidelity code transformations preserving formatting
# splurge-unittest-to-pytest — Detailed Reference

This file documents the current state of the tool: features, CLI reference, examples, and the programmatic API. It intentionally reflects the current behavior and does not describe legacy or historical behaviors.

Table of contents
- Overview
- Features
- CLI reference (exhaustive)
- Examples (CLI and programmatic)
- Notes on safety and limitations

Overview
--------
splurge-unittest-to-pytest converts Python unittest-based test suites to pytest style using safe, AST/CST-based transformations. The goal is to preserve test semantics while producing idiomatic pytest code.

Features
--------
- CST-based transformations using `libcst` for stable, semantics-preserving edits.
- Converts `unittest.TestCase` classes and test methods into pytest-style functions and fixtures.
- Merges `setUp`/`tearDown` into pytest fixtures when appropriate.
- Converts common `unittest` assertions to direct `assert` statements or pytest helpers.
- Dry-run preview modes: print converted content, show unified diffs, or list files.
- Preserves the original file extension by default. Use `--ext` to override the extension.
- Backups: enable `--backup` to keep copy of originals before overwriting.
- Formatting: generated code is always formatted with `black` and `isort`.
- Import optimization and safe removal of unused `unittest` imports.

CLI reference
-------------
All flags are available on the `migrate` command. This is an exhaustive, current reference.

- `-d, --dir DIR` : Root directory for input discovery.
- `-f, --file PATTERN` : Glob pattern(s) to select files. Repeatable. Default: `test_*.py`.
- `-r, --recurse / --no-recurse` : Recurse directories (default: recurse).
-- `-t, --target-dir DIR` : Directory to write outputs.
-- `--preserve-structure / --no-preserve-structure` : Keep original directory structure (default: preserve).
-- `--backup / --no-backup` : Create a `.backup` copy of originals when writing (default: backup).
-- `--merge-setup / --no-merge-setup` : Merge `setUp`/`tearDown` into fixtures (default: on).
- `--line-length N` : Max line length used by formatter (default: 120).
- `--dry-run` : Do not write files, produce preview output instead.
	- With `--dry-run --diff`: show unified diffs.
	- With `--dry-run --list`: list files only.
- `--ext EXT` : Override the target file extension (e.g., `py`, `.txt`). Default is to preserve the original extension.
- `--suffix SUFFIX` : Append the suffix to the target filename stem when writing.
- `--fail-fast` : Stop on first error (default: off).
- `-v, --verbose` : Verbose logging (default: off).
- `--report / --no-report` : Generate a migration report (default: on).
- `--report-format [json|html|markdown]` : Report format (default: json).
- `--config FILE` : Load configuration from YAML file.
- `--prefix PREFIX` : Allowed test method prefixes; repeatable (default: `test`).

Examples
--------

Preview a single file (print converted code):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/test_example.py --dry-run
```

Show unified diffs for a directory:

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/ -r --dry-run --diff
```

Write changes to a target directory with backups (formatting is always applied):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/ -r -t converted --backup
```

Override extension (write `.txt` files instead of `.py`):

```bash
python -m splurge_unittest_to_pytest.cli migrate tests/test_example.py --ext txt
```

Programmatic API
-----------------

Call `main.migrate(files: list[str], config: MigrationConfig)` to run migrations from Python code. The function returns a `Result` containing migrated paths and optional metadata (e.g., generated code when `dry_run=True`).

Example:

```python
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig

config = MigrationConfig(dry_run=True)
result = main.migrate(["tests/test_example.py"], config=config)
if result.is_success():
		# For dry-run, metadata may contain a 'generated_code' mapping
		gen_map = result.metadata.get("generated_code", {})
		print(gen_map)
else:
		print("Migration failed:", result.error)
```

Safety and limitations
----------------------

- The tool focuses on common unittest patterns and conservative transformations. Complex or highly dynamic test code may not be automatically converted.
- All transformations are implemented to minimize behavioral changes, but users should inspect diffs (use `--dry-run --diff`) and run their test suites after migration.
- Use `--backup` to retain originals when writing.

Notes
-----
- This document is up-to-date with the current release behavior and intentionally omits discussion of previously used legacy naming behaviors.

Recent updates
--------------

- Added focused unit tests for `splurge_unittest_to_pytest.transformers.assert_transformer` to exercise
	the libcst-based wrap/alias rewrite logic and string-fallbacks. These tests cover assertWarns/assertRaises/assertLogs/assertNoLogs
	conversions into pytest contexts and `caplog` usage patterns.
- Added tests to validate `assertAlmostEqual` -> `pytest.approx` conversions and membership/equality rewrites that call `.getMessage()` where appropriate.
- These are test-only changes intended to raise confidence in the transformer passes; no production API behavior was changed.
