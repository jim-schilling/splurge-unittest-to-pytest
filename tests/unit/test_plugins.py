"""Tests for plugin functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from splurge_unittest_to_pytest.plugins import (
    PluginInfo,
    PluginManager,
    TransformationPlugin,
    get_plugin_manager,
)
from splurge_unittest_to_pytest.result import Result


class MockPlugin:
    """Mock plugin for testing."""

    def __init__(self):
        self.name = "mock_plugin"
        self.version = "1.0.0"
        self.description = "A mock plugin for testing"

    def can_handle(self, node, context):
        """Mock can_handle method."""
        return isinstance(node, str) and "mock" in node

    def transform(self, node, context):
        """Mock transform method."""
        if isinstance(node, str):
            return Result.success(f"mock_transformed_{node}")
        return Result.failure(ValueError("Invalid node type"))


class TestPluginInfo:
    """Test PluginInfo dataclass."""

    def test_plugin_info_creation(self):
        """Test PluginInfo creation."""
        plugin_class = MockPlugin
        info = PluginInfo(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            module_path="/path/to/plugin.py",
            plugin_class=plugin_class,
            enabled=True,
        )

        assert info.name == "test_plugin"
        assert info.version == "1.0.0"
        assert info.description == "Test plugin"
        assert info.module_path == "/path/to/plugin.py"
        assert info.plugin_class == plugin_class
        assert info.enabled is True

    def test_plugin_info_defaults(self):
        """Test PluginInfo default values."""
        info = PluginInfo(
            name="test",
            version="1.0",
            description="Test",
            module_path="/path",
            plugin_class=MockPlugin,
        )

        assert info.enabled is True


class TestPluginManager:
    """Test PluginManager class."""

    def test_initialization(self):
        """Test PluginManager initialization."""
        manager = PluginManager()
        assert len(manager.plugins) == 0
        assert len(manager._loaded_plugins) == 0

    def test_register_plugin(self):
        """Test plugin registration."""
        manager = PluginManager()
        plugin_class = MockPlugin

        info = PluginInfo(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            module_path="/test/plugin.py",
            plugin_class=plugin_class,
        )

        # Register plugin
        result = manager.register_plugin(info)
        assert result is True
        assert "test_plugin" in manager.plugins
        assert manager.plugins["test_plugin"] == info

    def test_register_duplicate_plugin(self):
        """Test registering a duplicate plugin."""
        manager = PluginManager()

        info1 = PluginInfo(
            name="duplicate",
            version="1.0.0",
            description="First plugin",
            module_path="/test1.py",
            plugin_class=MockPlugin,
        )

        info2 = PluginInfo(
            name="duplicate",
            version="2.0.0",
            description="Second plugin",
            module_path="/test2.py",
            plugin_class=MockPlugin,
        )

        # Register first plugin
        assert manager.register_plugin(info1) is True

        # Try to register duplicate
        assert manager.register_plugin(info2) is False

        # First plugin should still be registered
        assert manager.plugins["duplicate"] == info1

    def test_enable_disable_plugin(self):
        """Test enabling and disabling plugins."""
        manager = PluginManager()

        info = PluginInfo(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            module_path="/test/plugin.py",
            plugin_class=MockPlugin,
        )

        manager.register_plugin(info)

        # Initially enabled
        assert manager.plugins["test_plugin"].enabled is True

        # Disable
        assert manager.disable_plugin("test_plugin") is True
        assert manager.plugins["test_plugin"].enabled is False

        # Enable
        assert manager.enable_plugin("test_plugin") is True
        assert manager.plugins["test_plugin"].enabled is True

        # Try to enable/disable non-existent plugin
        assert manager.enable_plugin("nonexistent") is False
        assert manager.disable_plugin("nonexistent") is False

    def test_get_plugin(self):
        """Test getting plugin instances."""
        manager = PluginManager()

        info = PluginInfo(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            module_path="/test/plugin.py",
            plugin_class=MockPlugin,
        )

        manager.register_plugin(info)

        # Get plugin instance
        plugin = manager.get_plugin("test_plugin")
        assert plugin is not None
        assert isinstance(plugin, MockPlugin)

        # Get same instance again (should be cached)
        plugin2 = manager.get_plugin("test_plugin")
        assert plugin is plugin2

        # Disable and try to get
        manager.disable_plugin("test_plugin")
        plugin3 = manager.get_plugin("test_plugin")
        assert plugin3 is None

        # Try to get non-existent plugin
        plugin4 = manager.get_plugin("nonexistent")
        assert plugin4 is None

    def test_find_plugins_for_node(self):
        """Test finding plugins that can handle a node."""
        manager = PluginManager()

        # Register mock plugin
        info = PluginInfo(
            name="mock_plugin",
            version="1.0.0",
            description="Mock plugin",
            module_path="/mock.py",
            plugin_class=MockPlugin,
        )
        manager.register_plugin(info)

        # Find plugins for a node that the mock plugin can handle
        capable_plugins = manager.find_plugins_for_node("this is a mock node", {})
        assert len(capable_plugins) == 1
        assert isinstance(capable_plugins[0], MockPlugin)

        # Find plugins for a node that the mock plugin cannot handle
        incapable_plugins = manager.find_plugins_for_node("this is a regular node", {})
        assert len(incapable_plugins) == 0

    def test_apply_plugins(self):
        """Test applying plugins to transform nodes."""
        manager = PluginManager()

        # Register mock plugin
        info = PluginInfo(
            name="mock_plugin",
            version="1.0.0",
            description="Mock plugin",
            module_path="/mock.py",
            plugin_class=MockPlugin,
        )
        manager.register_plugin(info)

        # Apply plugin to transformable node
        result = manager.apply_plugins("mock input", {})
        assert result.is_success()
        assert result.unwrap() == "mock_transformed_mock input"

        # Apply plugin to non-transformable node
        result = manager.apply_plugins("regular input", {})
        assert result.is_error()
        assert "No plugins available" in str(result.error)

    def test_plugin_discovery(self):
        """Test plugin discovery from directories."""
        manager = PluginManager()

        # Create temporary directory with plugin file
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_file = Path(temp_dir) / "test_plugin.py"
            plugin_file.write_text("""
class TestPlugin:
    name = "discovered_plugin"
    version = "1.0.0"
    description = "A discovered plugin"

    def can_handle(self, node, context):
        return isinstance(node, str)

    def transform(self, node, context):
        return "discovered_transformed"
""")

            # Discover plugins
            discovered = manager.discover_plugins([temp_dir])
            assert len(discovered) == 1
            assert discovered[0].name == "discovered_plugin"
            assert discovered[0].version == "1.0.0"

    def test_plugin_discovery_nonexistent_directory(self):
        """Test plugin discovery with nonexistent directory."""
        manager = PluginManager()

        # Should not crash with nonexistent directory
        discovered = manager.discover_plugins(["/nonexistent/path"])
        assert len(discovered) == 0

    def test_plugin_discovery_invalid_file(self):
        """Test plugin discovery with invalid plugin file."""
        manager = PluginManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid plugin file
            invalid_plugin = Path(temp_dir) / "invalid_plugin.py"
            invalid_plugin.write_text("invalid syntax {{{")

            # Should handle errors gracefully
            discovered = manager.discover_plugins([temp_dir])
            assert len(discovered) == 0

    def test_validate_plugin_compatibility(self):
        """Test plugin compatibility validation."""
        manager = PluginManager()

        # Register valid plugin
        info = PluginInfo(
            name="valid_plugin",
            version="1.0.0",
            description="Valid plugin",
            module_path="/valid.py",
            plugin_class=MockPlugin,
        )
        manager.register_plugin(info)

        # Validate compatibility
        result = manager.validate_plugin_compatibility("valid_plugin")
        assert result.is_success()
        assert result.unwrap() is True

        # Try to validate non-existent plugin
        result = manager.validate_plugin_compatibility("nonexistent")
        assert result.is_error()
        assert "not registered" in str(result.error)

    def test_list_plugins(self):
        """Test listing all plugins."""
        manager = PluginManager()

        # Register some plugins
        info1 = PluginInfo(
            name="plugin1",
            version="1.0.0",
            description="First plugin",
            module_path="/plugin1.py",
            plugin_class=MockPlugin,
            enabled=True,
        )

        info2 = PluginInfo(
            name="plugin2",
            version="2.0.0",
            description="Second plugin",
            module_path="/plugin2.py",
            plugin_class=MockPlugin,
            enabled=False,
        )

        manager.register_plugin(info1)
        manager.register_plugin(info2)

        # List plugins
        plugin_list = manager.list_plugins()
        assert len(plugin_list) == 2

        # Check plugin data
        plugin_names = {p["name"] for p in plugin_list}
        assert plugin_names == {"plugin1", "plugin2"}

        plugin1_data = next(p for p in plugin_list if p["name"] == "plugin1")
        assert plugin1_data["version"] == "1.0.0"
        assert plugin1_data["enabled"] is True

    def test_plugin_lifecycle(self):
        """Test complete plugin lifecycle."""
        manager = PluginManager()

        # Register plugin
        info = PluginInfo(
            name="lifecycle_plugin",
            version="1.0.0",
            description="Lifecycle test plugin",
            module_path="/lifecycle.py",
            plugin_class=MockPlugin,
        )
        manager.register_plugin(info)

        # Verify initial state
        assert manager.plugins["lifecycle_plugin"].enabled is True

        # Get plugin (loads it)
        plugin = manager.get_plugin("lifecycle_plugin")
        assert plugin is not None

        # Disable plugin
        manager.disable_plugin("lifecycle_plugin")
        assert manager.plugins["lifecycle_plugin"].enabled is False

        # Try to get disabled plugin
        disabled_plugin = manager.get_plugin("lifecycle_plugin")
        assert disabled_plugin is None

        # Re-enable plugin
        manager.enable_plugin("lifecycle_plugin")
        assert manager.plugins["lifecycle_plugin"].enabled is True

        # Get plugin again (should work now)
        reenabled_plugin = manager.get_plugin("lifecycle_plugin")
        assert reenabled_plugin is not None


class TestGlobalPluginManager:
    """Test global plugin manager."""

    def test_get_plugin_manager(self):
        """Test getting the global plugin manager."""
        manager = get_plugin_manager()
        assert isinstance(manager, PluginManager)

        # Should return the same instance
        manager2 = get_plugin_manager()
        assert manager is manager2


class TestPluginInterface:
    """Test plugin interface protocol."""

    def test_plugin_interface_compliance(self):
        """Test that MockPlugin complies with TransformationPlugin protocol."""
        plugin = MockPlugin()

        # Check required attributes
        assert hasattr(plugin, "name")
        assert hasattr(plugin, "version")
        assert hasattr(plugin, "description")
        assert hasattr(plugin, "can_handle")
        assert hasattr(plugin, "transform")

        # Test methods
        assert plugin.can_handle("mock node", {}) is True
        assert plugin.can_handle("regular node", {}) is False

        result = plugin.transform("test node", {})
        assert result.is_success()
        assert result.unwrap() == "mock_transformed_test node"

        # Test invalid input
        result = plugin.transform(123, {})
        assert result.is_error()


class TestPluginDiscoveryEdgeCases:
    """Test plugin discovery edge cases."""

    def test_discovery_with_mixed_files(self):
        """Test discovery with a mix of valid and invalid files."""
        manager = PluginManager()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a valid plugin file
            valid_plugin = temp_path / "valid_plugin.py"
            valid_plugin.write_text("""
class ValidPlugin:
    name = "valid_plugin"
    version = "1.0.0"
    description = "Valid plugin"

    def can_handle(self, node, context):
        return True

    def transform(self, node, context):
        return "transformed"
""")

            # Create a file without plugin class
            no_plugin = temp_path / "no_plugin.py"
            no_plugin.write_text("# Just a regular Python file")

            # Create a file with syntax error
            syntax_error = temp_path / "syntax_error.py"
            syntax_error.write_text("invalid syntax {{{{")

            # Discover plugins
            discovered = manager.discover_plugins([temp_dir])
            assert len(discovered) == 1
            assert discovered[0].name == "valid_plugin"

    def test_discovery_with_multiple_directories(self):
        """Test discovery across multiple directories."""
        manager = PluginManager()

        with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
            # Plugin in first directory
            plugin1 = Path(temp_dir1) / "plugin1.py"
            plugin1.write_text("""
class Plugin1:
    name = "plugin1"
    version = "1.0.0"
    description = "Plugin 1"

    def can_handle(self, node, context):
        return True

    def transform(self, node, context):
        return "transformed1"
""")

            # Plugin in second directory
            plugin2 = Path(temp_dir2) / "plugin2.py"
            plugin2.write_text("""
class Plugin2:
    name = "plugin2"
    version = "1.0.0"
    description = "Plugin 2"

    def can_handle(self, node, context):
        return True

    def transform(self, node, context):
        return "transformed2"
""")

            # Discover from both directories
            discovered = manager.discover_plugins([temp_dir1, temp_dir2])
            assert len(discovered) == 2

            plugin_names = {p.name for p in discovered}
            assert plugin_names == {"plugin1", "plugin2"}
