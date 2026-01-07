"""
Plugin Manager - Core component for managing EVOX plugins

This module provides the core logic for plugin management,
including dependency resolution, status tracking, and service discovery.
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Tuple
import tomli
import asyncio
from enum import Enum
from ..registry.registry import get_service_registry, ServiceInfo


class PluginStatus(Enum):
    """Status of a plugin"""
    INSTALLED = "installed"
    MISSING_DEPS = "missing_deps"
    INACTIVE = "inactive"


class PluginManager:
    """
    Plugin Manager - Core logic for managing EVOX plugins
    
    Handles plugin installation, dependency resolution, status tracking,
    and service discovery without any CLI-specific logic.
    """
    
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.plugins_path = self.project_root / "plugins"
        self._config_cache: Dict[str, Any] = {}
    
    def install_plugin(self, source: str) -> bool:
        """
        Install a plugin from the given source.
        
        Args:
            source: Source of the plugin (local path, git URL, or package name)
            
        Returns:
            True if plugin was installed successfully, False otherwise
        """
        # For local directories, copy the plugin
        source_path = Path(source)
        if source_path.exists() and source_path.is_dir():
            # Copy plugin directory to plugins folder
            plugin_name = source_path.name
            target_path = self.plugins_path / plugin_name
            
            if target_path.exists():
                print(f"Plugin '{plugin_name}' already exists!")
                return False
            
            # Create plugins directory if it doesn't exist
            self.plugins_path.mkdir(exist_ok=True)
            
            # Copy the plugin directory
            import shutil
            shutil.copytree(source_path, target_path)
            return True
        
        # For other sources (git, pypi), we'd implement different logic
        # For now, we'll just return False for unsupported sources
        print(f"Unsupported plugin source: {source}")
        return False
    
    def sync_dependencies(self) -> bool:
        """
        Sync dependencies for all plugins using rye.
        
        Returns:
            True if sync was successful, False otherwise
        """
        # Check if rye is available
        try:
            result = subprocess.run(["rye", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            has_rye = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("Error: rye not found in the system")
            return False
        
        if not has_rye:
            print("Error: rye not found in the system")
            return False
        
        # Run rye sync to install dependencies
        try:
            result = subprocess.run(["rye", "sync"], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"Error running 'rye sync': {result.stderr}")
                return False
            return True
        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"Error syncing dependencies: {e}")
            return False
    
    def get_plugin_status(self, plugin_name: str) -> PluginStatus:
        """
        Determine the status of a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            PluginStatus indicating the state of the plugin
        """
        plugin_path = self.plugins_path / plugin_name
        if not plugin_path.exists():
            return PluginStatus.INACTIVE
        
        # Check if config exists
        config_path = plugin_path / "config.toml"
        if not config_path.exists():
            return PluginStatus.INACTIVE
        
        # Try to load the plugin to check for missing dependencies
        try:
            # Add plugin path to Python path temporarily
            plugin_path_str = str(plugin_path.absolute())
            if plugin_path_str not in sys.path:
                sys.path.insert(0, plugin_path_str)
            
            # Try to import the main module
            main_py = plugin_path / "main.py"
            if main_py.exists():
                spec = importlib.util.spec_from_file_location(f"{plugin_name}_module", main_py)
                module = importlib.util.module_from_spec(spec)
                # Don't execute to avoid side effects, just check if it can be parsed
                spec.loader.exec_module(module)
            
            # Remove path from sys.path
            if plugin_path_str in sys.path:
                sys.path.remove(plugin_path_str)
                
            return PluginStatus.INSTALLED
        except ImportError:
            return PluginStatus.MISSING_DEPS
        except Exception:
            return PluginStatus.INACTIVE
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        List all plugins in the project.
        
        Returns:
            List of plugin information dictionaries
        """
        if not self.plugins_path.exists():
            return []
        
        plugins = []
        for plugin_dir in self.plugins_path.iterdir():
            if plugin_dir.is_dir():
                config_path = plugin_dir / "config.toml"
                config = {}
                
                if config_path.exists():
                    try:
                        with open(config_path, "rb") as f:
                            config = tomli.load(f)
                    except Exception:
                        pass  # Config file is malformed or doesn't exist
                
                plugin_info = {
                    "name": plugin_dir.name,
                    "path": str(plugin_dir),
                    "config": config,
                    "status": self.get_plugin_status(plugin_dir.name)
                }
                plugins.append(plugin_info)
        
        return plugins
    
    def resolve_dependencies(self) -> Dict[str, List[str]]:
        """
        Resolve dependencies for all plugins by scanning config.toml files.
        
        Returns:
            Dictionary mapping plugin names to their dependencies
        """
        dependencies = {}
        
        for plugin_info in self.list_plugins():
            plugin_name = plugin_info["name"]
            config = plugin_info["config"]
            
            # Extract dependencies from config
            plugin_deps = config.get("service", {}).get("prerequisites", [])
            dependencies[plugin_name] = plugin_deps
        
        return dependencies
    
    def get_plugin_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find plugins that provide a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of plugin information that provide the capability
        """
        matching_plugins = []
        
        for plugin_info in self.list_plugins():
            config = plugin_info["config"]
            capabilities = config.get("service", {}).get("capabilities", [])
            
            if capability in capabilities:
                matching_plugins.append(plugin_info)
        
        return matching_plugins
    
    def validate_plugin_structure(self, plugin_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate that a plugin has the required structure.
        
        Args:
            plugin_path: Path to the plugin directory
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if main.py exists
        main_py = plugin_path / "main.py"
        if not main_py.exists():
            errors.append("Missing main.py file")
        
        # Check if config.toml exists
        config_toml = plugin_path / "config.toml"
        if not config_toml.exists():
            errors.append("Missing config.toml file")
        
        # If both files exist, try to parse config.toml
        if config_toml.exists():
            try:
                with open(config_toml, "rb") as f:
                    config = tomli.load(f)
                
                # Check for required fields in service config
                service_config = config.get("service", {})
                if "name" not in service_config:
                    errors.append("Missing 'name' in [service] section of config.toml")
                if "port" not in service_config:
                    errors.append("Missing 'port' in [service] section of config.toml")
            except Exception as e:
                errors.append(f"Invalid config.toml: {str(e)}")
        
        return len(errors) == 0, errors
    
    def create_plugin_template(self, name: str, plugin_type: str = "generic") -> bool:
        """
        Create a new plugin template with the specified type.
        
        Args:
            name: Name of the plugin
            plugin_type: Type of plugin to create (e.g., "storage")
            
        Returns:
            True if plugin was created successfully, False otherwise
        """
        plugin_path = self.plugins_path / name
        
        # Check if plugin already exists
        if plugin_path.exists():
            print(f"Plugin '{name}' already exists!")
            return False
        
        # Create plugin directory
        plugin_path.mkdir(parents=True, exist_ok=True)
        
        # Create the plugin files based on type
        if plugin_type == "storage":
            return self._create_storage_plugin(plugin_path, name)
        else:
            return self._create_generic_plugin(plugin_path, name)
    
    def _create_generic_plugin(self, plugin_path: Path, name: str) -> bool:
        """Create a generic plugin template"""
        # Create config.toml
        config_content = f"""# EVOX Plugin Configuration\n\n[service]\nname = \"{name}\"\nport = 8000\nprerequisites = []\ncapabilities = [\"generic\"]\n\n[plugin]\ntype = \"generic\"\nversion = \"0.0.1\"\n"""
        
        config_path = plugin_path / "config.toml"
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Create main.py
        main_content = f"""\nimport asyncio\nfrom evox.core.inject import inject\n\n\nclass {name.title().replace('-', '')}Plugin:\n    def __init__(self):\n        self.name = \"{name}\"\n        \n    async def start(self):\n        print(f\"Starting {{self.name}} plugin...\")\n        \n    async def stop(self):\n        print(f\"Stopping {{self.name}} plugin...\")\n\n\n# Plugin factory function\nasync def create_plugin():\n    return {name.title().replace('-', '')}Plugin()\n\n\nif __name__ == \"__main__\":\n    # For testing the plugin directly\n    import asyncio\n    plugin = asyncio.run(create_plugin())\n    asyncio.run(plugin.start())\n"""
        main_path = plugin_path / "main.py"
        with open(main_path, 'w') as f:
            f.write(main_content)
        
        return True
    
    def _create_storage_plugin(self, plugin_path: Path, name: str) -> bool:
        """Create a storage plugin template"""
        # Create config.toml
        config_content = f"""# EVOX Storage Plugin Configuration\n\n[service]\nname = \"{name}\"\nport = 8000\nprerequisites = []\ncapabilities = [\"storage\", \"provider\"]\n\n[plugin]\ntype = \"storage\"\nversion = \"0.0.1\"\n\n[storage]\nprovider = \"{name}\"\nconnection_timeout = 30\nhealth_check_interval = 60\n"""
        
        config_path = plugin_path / "config.toml"
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Create main.py
        main_content = f"""\nimport asyncio\nfrom evox.core.storage_provider import StorageProviderProtocol\nfrom evox.core.intents import Intent\n\n\nclass {name.title().replace('-', '')}StorageProvider(StorageProviderProtocol):\n    \"\"\"Storage provider for {name}\"\"\"\n    \n    def __init__(self):\n        self._is_healthy = True\n        self._config = {{}}\n        \n    async def read(self, key: str, intent: Intent = Intent.STANDARD) -> any:\n        \"\"\"Read data by key\"\"\"\n        # Implement read logic here\n        return None\n    \n    async def write(self, key: str, value: any, intent: Intent = Intent.STANDARD) -> bool:\n        \"\"\"Write data with key\"\"\"\n        # Implement write logic here\n        return True\n    \n    async def delete(self, key: str, intent: Intent = Intent.STANDARD) -> bool:\n        \"\"\"Delete data by key\"\"\"\n        # Implement delete logic here\n        return True\n    \n    async def check_health(self) -> bool:\n        \"\"\"Check provider health\"\"\"\n        # Implement health check logic here\n        return self._is_healthy\n    \n    @property\n    def is_healthy(self) -> bool:\n        \"\"\Get health status\"\"\"\n        return self._is_healthy\n    \n    @property\n    def provider_properties(self) -> dict:\n        \"\"\Get provider properties\"\"\"\n        return {{\n            \"type\": \"{name}\",\n            \"supports_transactions\": False,\n            \"supports_replication\": False\n        }}\n\n\n# Plugin factory function\nasync def create_provider():\n    return {name.title().replace('-', '')}StorageProvider()\n\n\nif __name__ == \"__main__\":\n    # For testing the storage provider directly\n    import asyncio\n    provider = asyncio.run(create_provider())\n    print(f\"{name} storage provider created.\")\n    print(f\"Health: {{await provider.check_health()}}\")\n"""
        main_path = plugin_path / "main.py"
        with open(main_path, 'w') as f:
            f.write(main_content)
        
        return True


# Global plugin manager instance
_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Returns:
        PluginManager instance
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


__all__ = [
    "PluginManager",
    "PluginStatus",
    "get_plugin_manager"
]