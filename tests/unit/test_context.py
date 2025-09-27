"""Tests for the context and configuration system."""

import tempfile
from pathlib import Path

from splurge_unittest_to_pytest.context import FixtureScope, MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.result import Result


def test_migration_config_creation():
    """Test creating migration configuration with defaults."""
    config = MigrationConfig()

    assert config.format_code is True
    assert config.line_length == 120
    assert config.preserve_structure is True
    assert config.convert_classes_to_functions is True
    assert config.fixture_scope == FixtureScope.FUNCTION


def test_migration_config_with_overrides():
    """Test creating migration configuration with custom values."""
    config = MigrationConfig(format_code=False, line_length=100, dry_run=True, fixture_scope=FixtureScope.CLASS)

    assert config.format_code is False
    assert config.line_length == 100
    assert config.dry_run is True
    assert config.fixture_scope == FixtureScope.CLASS


def test_migration_config_with_override():
    """Test using with_override method."""
    config = MigrationConfig(format_code=True, line_length=80)
    new_config = config.with_override(format_code=False, line_length=120)

    assert config.format_code is True
    assert config.line_length == 80
    assert new_config.format_code is False
    assert new_config.line_length == 120


def test_migration_config_to_dict():
    """Test converting config to dictionary."""
    config = MigrationConfig(format_code=False, line_length=100)
    config_dict = config.to_dict()

    assert config_dict["format_code"] is False
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
    import tempfile

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
    import tempfile

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file for config testing")
        temp_file = f.name

    try:
        config = MigrationConfig(format_code=True)
        context = PipelineContext.create(source_file=temp_file, config=config)

        new_context = context.with_config(format_code=False, line_length=100)

        assert context.config.format_code is True
        assert context.config.line_length == 120
        assert new_context.config.format_code is False
        assert new_context.config.line_length == 100
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_pipeline_context_getters():
    """Test pipeline context getter methods."""
    import os
    import tempfile

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file for getters testing")
        temp_file = f.name

    try:
        config = MigrationConfig(dry_run=True, format_code=False, line_length=100)
        context = PipelineContext.create(source_file=temp_file, config=config)

        assert context.is_dry_run() is True
        assert context.should_format_code() is False
        assert context.get_line_length() == 100
    finally:
        # Clean up the temporary file
        os.unlink(temp_file)


def test_pipeline_context_immutability():
    """Test that pipeline context is immutable."""
    import os
    import tempfile

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Test file for immutability testing")
        temp_file = f.name

    try:
        config = MigrationConfig()
        context = PipelineContext.create(source_file=temp_file, config=config)

        # All these should create new instances
        context1 = context.with_metadata("key", "value")
        context2 = context.with_config(format_code=False)

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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
format_code: false
line_length: 100
dry_run: true
"""
        )
        config_file = f.name

    try:
        result = MigrationConfig.from_dict({"format_code": False, "line_length": 100, "dry_run": True})
        assert result.format_code is False
        assert result.line_length == 100
        assert result.dry_run is True

    finally:
        Path(config_file).unlink()


def test_config_validation():
    """Test configuration validation."""
    # Valid config
    config = MigrationConfig(max_workers=4, line_length=100, report_format="json")
    # Use the config variable to avoid unused variable warning
    assert config.max_workers == 4

    # Invalid configs
    invalid_config1 = MigrationConfig(max_workers=0)
    invalid_config2 = MigrationConfig(line_length=50)
    invalid_config3 = MigrationConfig(report_format="invalid")

    # These should be invalid
    assert invalid_config1.max_workers == 0
    assert invalid_config2.line_length == 50
    assert invalid_config3.report_format == "invalid"
