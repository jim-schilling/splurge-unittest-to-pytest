"""Small adapters that coerce CLI runtime values into strongly-typed objects.

These helpers live at the CLI boundary and make it easy to keep the rest of
the library strictly typed while keeping the CLI thin. They intentionally
perform defensive coercions (OptionInfo -> native types) and only expose
concrete standard library types to callers.
"""

from __future__ import annotations

from typing import Any

from .context import MigrationConfig


def _unwrap_option(value: Any) -> Any:
    """If the value is a Typer/Click OptionInfo-like object, unwrap the default.

    We don't import Typer here to avoid tight runtime coupling in tests; instead
    we use a duck-typing approach: OptionInfo objects normally expose a
    ``default`` attribute.
    """
    if hasattr(value, "default"):
        try:
            return value.default
        except Exception:
            return value
    return value


def build_config_from_cli(base_config: MigrationConfig, cli_kwargs: dict[str, object]) -> MigrationConfig:
    """Construct a typed MigrationConfig by coercing CLI-provided values.

    Args:
        base_config: The baseline MigrationConfig instance to override.
        cli_kwargs: Dictionary of candidate overrides produced by the CLI.

    Returns:
        A new MigrationConfig instance with overrides applied.

    Raises:
        ValueError: If any coerced value is invalid for the configuration.
    """
    filtered: dict[str, Any] = {}

    # Obtain a set of valid fields from the dataclass to filter unknown keys
    valid_fields = set(MigrationConfig.__dataclass_fields__.keys())

    for key, raw_val in cli_kwargs.items():
        if key not in valid_fields:
            # Leave unknown keys for other CLI handlers (e.g., enhanced features)
            continue

        val = _unwrap_option(raw_val)

        # Coerce common primitive types used by the CLI
        if val is None:
            # Explicit None means the CLI did not set a value; skip override
            continue

        # Integer coercions
        if key in {"assert_almost_equal_places", "max_file_size_mb", "max_concurrent_files", "max_depth"}:
            try:
                filtered[key] = int(val)
            except Exception as e:
                raise ValueError(f"Configuration value for {key} must be an integer: {val}") from e
            continue

        # Boolean-like values
        if key in {
            "dry_run",
            "fail_fast",
            "backup_originals",
            "format_output",
            "remove_unused_imports",
            "preserve_import_comments",
            "transform_assertions",
            "transform_setup_teardown",
            "transform_subtests",
            "transform_skip_decorators",
            "transform_imports",
            "continue_on_error",
            "cache_analysis_results",
            "preserve_file_encoding",
            "create_source_map",
        }:
            filtered[key] = bool(val)
            continue

        # Lists
        if key in {"file_patterns", "test_method_prefixes"}:
            if isinstance(val, str):
                # Allow comma-separated lists as a convenience
                filtered[key] = [p.strip() for p in val.split(",") if p.strip()]
            elif isinstance(val, list | tuple | set):
                filtered[key] = list(val)
            else:
                filtered[key] = [val]
            continue

        # Default: use string conversion for safety where appropriate
        filtered[key] = val

    # Apply overrides using the dataclass helper; this will validate the
    # resulting configuration via MigrationConfig.validate()
    # Return a MigrationConfig with applied overrides. Validation is intentionally
    # deferred to higher-level callers so the CLI remains forgiving and can
    # attempt fallbacks (for example, when enhanced validation is enabled).
    return base_config.with_override(**filtered)
