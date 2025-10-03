"""Plugin architecture for transformation extensibility.

This module defines the plugin interfaces and management system that allows
users to extend the transformation capabilities with custom plugins.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .result import Result

logger = logging.getLogger(__name__)


class TransformationPlugin(Protocol):
    """Protocol for transformation plugins."""

    name: str
    version: str
    description: str

    def can_handle(self, node: Any, context: Any) -> bool:
        """Check if this plugin can handle the given node/context."""
        ...

    def transform(self, node: Any, context: Any) -> Result[Any]:
        """Transform the given node using this plugin."""
        ...


@dataclass
class PluginInfo:
    """Information about a loaded plugin."""

    name: str
    version: str
    description: str
    module_path: str
    plugin_class: type[TransformationPlugin]
    enabled: bool = True


class PluginManager:
    """Manages loading and execution of transformation plugins."""

    def __init__(self):
        self.plugins: dict[str, PluginInfo] = {}
        self._loaded_plugins: dict[str, TransformationPlugin] = {}

    def discover_plugins(self, plugin_dirs: list[str]) -> list[PluginInfo]:
        """Discover plugins in the given directories.

        Args:
            plugin_dirs: List of directories to search for plugins

        Returns:
            List of discovered plugin information
        """
        discovered = []

        for plugin_dir in plugin_dirs:
            plugin_path = Path(plugin_dir)
            if not plugin_path.exists():
                continue

            # Look for Python files that might contain plugins
            for py_file in plugin_path.glob("*.py"):
                try:
                    plugin_info = self._load_plugin_from_file(py_file)
                    if plugin_info:
                        discovered.append(plugin_info)
                except Exception as e:
                    logger.warning(f"Failed to load plugin from {py_file}: {e}")

        return discovered

    def _load_plugin_from_file(self, file_path: Path) -> PluginInfo | None:
        """Load a plugin from a Python file."""
        try:
            # Import the module
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for plugin classes
            for _name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and hasattr(obj, "name")
                    and hasattr(obj, "version")
                    and hasattr(obj, "description")
                    and hasattr(obj, "can_handle")
                    and hasattr(obj, "transform")
                ):
                    plugin_info = PluginInfo(
                        name=obj.name,
                        version=obj.version,
                        description=obj.description,
                        module_path=str(file_path),
                        plugin_class=obj,
                    )
                    return plugin_info

        except Exception as e:
            logger.warning(f"Error loading plugin from {file_path}: {e}")

        return None

    def register_plugin(self, plugin_info: PluginInfo) -> bool:
        """Register a plugin with the manager.

        Args:
            plugin_info: Plugin information to register

        Returns:
            True if registration successful, False otherwise
        """
        if plugin_info.name in self.plugins:
            logger.warning(f"Plugin {plugin_info.name} already registered")
            return False

        self.plugins[plugin_info.name] = plugin_info
        logger.info(f"Registered plugin: {plugin_info.name} v{plugin_info.version}")
        return True

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin.

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            True if plugin was enabled, False if not found
        """
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = True
            # Remove from loaded plugins so it gets reloaded
            self._loaded_plugins.pop(plugin_name, None)
            logger.info(f"Enabled plugin: {plugin_name}")
            return True
        return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin.

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            True if plugin was disabled, False if not found
        """
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = False
            # Remove from loaded plugins
            self._loaded_plugins.pop(plugin_name, None)
            logger.info(f"Disabled plugin: {plugin_name}")
            return True
        return False

    def get_plugin(self, plugin_name: str) -> TransformationPlugin | None:
        """Get a loaded plugin instance.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            Plugin instance if available and enabled, None otherwise
        """
        if plugin_name not in self.plugins or not self.plugins[plugin_name].enabled:
            return None

        if plugin_name in self._loaded_plugins:
            return self._loaded_plugins[plugin_name]

        # Load the plugin
        try:
            plugin_class = self.plugins[plugin_name].plugin_class
            plugin_instance = plugin_class()
            self._loaded_plugins[plugin_name] = plugin_instance
            return plugin_instance
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {plugin_name}: {e}")
            return None

    def find_plugins_for_node(self, node: Any, context: Any) -> list[TransformationPlugin]:
        """Find all enabled plugins that can handle the given node.

        Args:
            node: The AST node to check
            context: The transformation context

        Returns:
            List of plugins that can handle the node
        """
        capable_plugins = []

        for plugin_name in self.plugins:
            if not self.plugins[plugin_name].enabled:
                continue

            plugin = self.get_plugin(plugin_name)
            if plugin and plugin.can_handle(node, context):
                capable_plugins.append(plugin)

        return capable_plugins

    def apply_plugins(self, node: Any, context: Any) -> Result[Any]:
        """Apply the first capable plugin to transform the node.

        Args:
            node: The AST node to transform
            context: The transformation context

        Returns:
            Result of the transformation
        """
        capable_plugins = self.find_plugins_for_node(node, context)

        if not capable_plugins:
            return Result.failure(ValueError("No plugins available for this node type"))

        # Try plugins in order (first one that can handle it)
        for plugin in capable_plugins:
            try:
                result = plugin.transform(node, context)
                if result.is_success():
                    logger.debug(f"Plugin {plugin.name} successfully transformed node")
                    return result
            except Exception as e:
                logger.warning(f"Plugin {plugin.name} failed: {e}")
                continue

        return Result.failure(ValueError("All capable plugins failed to transform the node"))

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins with their status.

        Returns:
            List of plugin information dictionaries
        """
        return [
            {
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "enabled": info.enabled,
                "module_path": info.module_path,
            }
            for info in self.plugins.values()
        ]

    def validate_plugin_compatibility(self, plugin_name: str) -> Result[bool]:
        """Validate that a plugin is compatible with the current system.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            Result indicating compatibility status
        """
        if plugin_name not in self.plugins:
            return Result.failure(ValueError(f"Plugin {plugin_name} not registered"))

        try:
            # Try to instantiate and test basic functionality
            plugin = self.get_plugin(plugin_name)
            if not plugin:
                return Result.failure(ValueError(f"Failed to load plugin {plugin_name}"))

            # Basic validation - check required attributes
            required_attrs = ["name", "version", "description", "can_handle", "transform"]
            for attr in required_attrs:
                if not hasattr(plugin, attr):
                    return Result.failure(ValueError(f"Plugin {plugin_name} missing required attribute: {attr}"))

            return Result.success(True)

        except Exception as e:
            return Result.failure(ValueError(f"Plugin {plugin_name} validation failed: {e}"))


# Global plugin manager instance
_plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    return _plugin_manager


def register_builtin_plugins():
    """Register the built-in transformation plugins."""
    # This will be called during system initialization
    # Built-in plugins would be registered here
    pass
