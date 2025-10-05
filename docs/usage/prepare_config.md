# prepare_config helper

The `prepare_config` helper is a convenience entrypoint that wires together the CLI helper functions used to prepare a `MigrationConfig` for use by the CLI or programmatic API.

Usage:

- Location: `splurge_unittest_to_pytest/cli_helpers.py`
- Function: `prepare_config(base_config=None, interactive=False, questions=None, enhanced_kwargs=None)`

Behavior:

- Applies non-interactive defaults using the questions list if provided.
- When `interactive=True`, runs interactive prompts to collect values.
- Attempts to apply enhanced validation and features; on failure it falls back to a basic `MigrationConfig`.

This entrypoint is designed to be used by the CLI and by tests that need a single, deterministic way to build the effective configuration.
