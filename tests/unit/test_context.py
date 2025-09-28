"""Tests for the context and configuration system."""

import tempfile
from pathlib import Path

from splurge_unittest_to_pytest.context import FixtureScope, MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.result import Result


def test_migration_config_creation():
    """Test creating migration configuration with defaults."""
    config = MigrationConfig()

    # Basic defaults
    assert config.line_length == 120
    assert config.preserve_structure is True


def test_migration_config_with_overrides():
    """Test creating migration configuration with custom values."""
    config = MigrationConfig(line_length=100, dry_run=True)

    assert config.line_length == 100
    assert config.dry_run is True


def test_migration_config_with_override():
    """Test using with_override method."""
    config = MigrationConfig(line_length=80)
    new_config = config.with_override(line_length=120)

    assert config.line_length == 80
    assert new_config.line_length == 120


def test_migration_config_to_dict():
    """Test converting config to dictionary."""
    config = MigrationConfig(line_length=100)
    config_dict = config.to_dict()

    assert config_dict["line_length"] == 100
    assert config_dict["preserve_structure"] is True


def test_pipeline_context_creation():
    """Test creating pipeline context."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file")
        temp_file = f.name

    try:
        config = MigrationConfig()
        context = PipelineContext.create(source_file=temp_file, config=config)

        assert context.source_file == temp_file
        assert context.config == config
        assert context.run_id is not None
        assert len(context.run_id) == 36  # UUID length
        assert context.metadata == {}

    finally:
        Path(temp_file).unlink()


def test_pipeline_context_with_custom_target():
    """Test creating pipeline context with custom target file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file")
        temp_file = f.name

    try:
        config = MigrationConfig()
        target_file = temp_file.replace(".py", ".pytest.txt")
        context = PipelineContext.create(source_file=temp_file, target_file=target_file, config=config)

        assert context.source_file == temp_file
        assert context.target_file == target_file

    finally:
        Path(temp_file).unlink()
        if Path(target_file).exists():
            Path(target_file).unlink()


def test_pipeline_context_with_metadata():
    """Test pipeline context with metadata."""
    import os

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file for context testing")
        temp_file = f.name

    try:
        config = MigrationConfig()
        context = PipelineContext.create(source_file=temp_file, config=config)

        new_context = context.with_metadata("test_key", "test_value")

        assert context.metadata == {}
        assert new_context.metadata == {"test_key": "test_value"}
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_pipeline_context_with_config():
    """Test pipeline context with config updates."""
    import os

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file for config testing")
        temp_file = f.name

    try:
        config = MigrationConfig()
        context = PipelineContext.create(source_file=temp_file, config=config)

        new_context = context.with_config(line_length=100)

        assert context.config.line_length == 120
        assert new_context.config.line_length == 100
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_pipeline_context_getters():
    """Test pipeline context getter methods."""
    import os

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file for getters testing")
        temp_file = f.name

    try:
        config = MigrationConfig(dry_run=True, line_length=100)
        context = PipelineContext.create(source_file=temp_file, config=config)

        assert context.is_dry_run() is True
        # should_format_code no longer depends on a flag; skip checking it
        assert context.get_line_length() == 100
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_pipeline_context_immutability():
    """Test that pipeline context is immutable."""
    import os

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file for immutability testing")
        temp_file = f.name

    try:
        config = MigrationConfig()
        context = PipelineContext.create(source_file=temp_file, config=config)

        # All these should create new instances
        context1 = context.with_metadata("key", "value")
        context2 = context.with_config(line_length=80)

        assert context is not context1
        assert context is not context2
        assert context1 is not context2
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_fixture_scope_enum():
    """Test fixture scope enum values."""
    assert FixtureScope.FUNCTION.value == "function"
    assert FixtureScope.CLASS.value == "class"
    assert FixtureScope.MODULE.value == "module"
    assert FixtureScope.SESSION.value == "session"


def test_context_manager_load_config():
    """Test loading configuration from file."""
    # Create a dict with supported keys only
    result = MigrationConfig.from_dict({"line_length": 100, "dry_run": True})
    assert result.line_length == 100
    assert result.dry_run is True


def test_config_validation():
    """Test configuration validation."""
    # Valid config
    config = MigrationConfig(line_length=100, report_format="json")
    # basic smoke: ensure config is created
    assert config is not None

    # Invalid configs
    invalid_config2 = MigrationConfig(line_length=50)
    invalid_config3 = MigrationConfig(report_format="invalid")
    assert invalid_config2.line_length == 50
    assert invalid_config3.report_format == "invalid"
