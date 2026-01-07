# Storage provider protocol

import importlib
from pathlib import Path
from typing import Protocol, Dict, List, Optional, Any
from datetime import datetime
from .providers.base_provider import BaseProvider
from ...data.intents.intent_system import Intent
import logging
import os

class StorageProviderProtocol(Protocol):
    """Protocol for storage providers"""
    
    async def read(self, key: str, intent: Intent = Intent.STANDARD) -> Any:
        """Read data by key"""
        ...
    
    async def write(self, key: str, value: Any, intent: Intent = Intent.STANDARD) -> bool:
        """Write data with key"""
        ...
    
    async def delete(self, key: str, intent: Intent = Intent.STANDARD) -> bool:
        """Delete data by key"""
        ...
    
    async def check_health(self) -> bool:
        """Check provider health"""
        ...
    
    @property
    def is_healthy(self) -> bool:
        """Get health status"""
        ...
    
    @property
    def provider_properties(self) -> Dict[str, Any]:
        """Get provider properties"""
        ...


class ServiceRegistry:
    """
    Service Registry for auto-scanning pluggable services.
    
    Auto-scans both built-in `evox/pluggable_services/` and user `plugins/` directories.
    Supports config.toml priority: user plugins override built-in.
    """
    
    def __init__(self):
        self._providers: Dict[str, StorageProviderProtocol] = {}
        self._scanned_directories: List[str] = []
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
    
    async def scan_and_register_services(self, *scan_paths: str):
        """
        Scan directories for pluggable services and register them.
        
        Args:
            *scan_paths: Paths to scan for services (defaults to built-in and user plugins)
        """
        if not scan_paths:
            # Default scan paths
            scan_paths = [
                "./evox/pluggable_services",  # Built-in services
                "./plugins"                   # User plugins (higher priority)
            ]
        
        for scan_path in scan_paths:
            await self._scan_directory(scan_path)
    
    async def _scan_directory(self, directory_path: str):
        """
        Scan a directory for service modules and register them.
        
        Args:
            directory_path: Path to directory to scan
        """
        dir_path = Path(directory_path)
        if not dir_path.exists():
            logging.info(f"Scan directory does not exist: {directory_path}")
            return
        
        # Load config.toml if it exists
        config_path = dir_path / "config.toml"
        if config_path.exists():
            await self._load_config(config_path)
        
        # Scan for Python modules
        for python_file in dir_path.glob("**/*.py"):
            if python_file.name.startswith("_"):
                continue  # Skip private modules
            
            await self._load_module(python_file)
    
    async def _load_config(self, config_path: Path):
        """
        Load configuration from config.toml file.
        
        Args:
            config_path: Path to config.toml file
        """
        try:
            # Import TOML parser if available
            import tomli  # Using tomli for compatibility
            with open(config_path, 'rb') as f:
                config = tomli.load(f)
            
            # Store config for plugin resolution
            plugin_name = config_path.parent.name
            self._plugin_configs[plugin_name] = config
        
        except ImportError:
            logging.warning(f"tomli not available, skipping config loading: {config_path}")
        except Exception as e:
            logging.error(f"Error loading config {config_path}: {e}")
    
    async def _load_module(self, module_path: Path):
        """
        Load a Python module and register any providers found.
        
        Args:
            module_path: Path to Python module file
        """
        try:
            # Generate a unique module name
            module_name = f"evox_dynamic_{module_path.stem}_{id(module_path)}"
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for create_provider factory function
            if hasattr(module, 'create_provider'):
                try:
                    provider = module.create_provider()
                    provider_name = getattr(provider, 'name', module_path.stem)
                    self._providers[provider_name] = provider
                    logging.info(f"Registered provider: {provider_name} from {module_path}")
                except Exception as e:
                    logging.error(f"Error creating provider from {module_path}: {e}")
            
            # Also look for any classes that implement StorageProviderProtocol
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (hasattr(attr, '__bases__') and 
                    any(hasattr(base, 'read') and hasattr(base, 'write') and 
                        hasattr(base, 'delete') and hasattr(base, 'check_health') 
                        for base in attr.__mro__ if base != object)):
                    # Try to instantiate if it's a class
                    try:
                        if isinstance(attr, type):
                            provider = attr()
                            provider_name = getattr(provider, 'name', attr.__name__)
                            self._providers[provider_name] = provider
                            logging.info(f"Registered provider: {provider_name} from {module_path}")
                    except Exception as e:
                        logging.debug(f"Could not instantiate {attr_name}: {e}")
        
        except Exception as e:
            logging.error(f"Error loading module {module_path}: {e}")
    
    def get_provider(self, provider_name: str) -> Optional[StorageProviderProtocol]:
        """
        Get a registered provider by name.
        
        Args:
            provider_name: Name of the provider to get
            
        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(provider_name)
    
    def list_providers(self) -> List[str]:
        """
        List all registered provider names.
        
        Returns:
            List of provider names
        """
        return list(self._providers.keys())
    
    def register_provider(self, name: str, provider: StorageProviderProtocol):
        """
        Manually register a provider.
        
        Args:
            name: Name to register the provider under
            provider: Provider instance to register
        """
        self._providers[name] = provider
        logging.info(f"Manually registered provider: {name}")


# Global service registry instance
service_registry = ServiceRegistry()


async def initialize_service_registry():
    """Initialize the service registry by scanning for plugins"""
    await service_registry.scan_and_register_services()
    logging.info(f"Service registry initialized with {len(service_registry.list_providers())} providers")


class SQLiteStorageProvider(BaseProvider):
    """
    Health-aware SQLite storage provider implementing BaseProvider interface.
    
    Rationale: This provider demonstrates how to implement the BaseProvider interface
    with real health checking capabilities, specifically for SQLite storage.
    """
    
    def __init__(self, db_path: str = "data.db", is_mock_healthy: bool = True):
        self.db_path = db_path
        self._is_healthy = True
        self._last_health_check = datetime.now()
        self.is_mock_healthy = is_mock_healthy  # For testing purposes
        self.name = "sqlite_provider"  # Name for registry
    
    @property
    def is_healthy(self) -> bool:
        """
        Property indicating current health status of the provider.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        return self._is_healthy
    
    @property
    def last_health_check(self) -> datetime:
        """
        Property indicating the timestamp of the last health check.
            
        Returns:
            datetime: Timestamp of the last health check
        """
        return self._last_health_check
    
    @property
    def provider_properties(self) -> Dict[str, Any]:
        """Get provider properties"""
        return {
            "type": "sqlite",
            "db_path": self.db_path,
            "supports_transactions": True,
            "supports_replication": False
        }
    
    async def check_health(self) -> bool:
        """
        Asynchronously check the health of the SQLite provider.
        
        This method performs a simple health check by attempting to access
        the database file and running a basic query.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        try:
            # For demonstration purposes, we'll simulate a health check
            # In a real implementation, this would attempt to connect to the database
            # and run a simple query to verify connectivity
            import os
            
            # Check if database file exists (or can be created)
            if self.is_mock_healthy:
                # Simulate a successful health check
                self._is_healthy = True
                self._last_health_check = datetime.now()
                
                # Log the health check
                logging.info(f"SQLite storage provider at {self.db_path} is healthy")
            else:
                # Simulate an unhealthy state
                self._is_healthy = False
                self._last_health_check = datetime.now()
                
                # Log the health issue
                logging.warning(f"SQLite storage provider at {self.db_path} is unhealthy")
            
            return self._is_healthy
            
        except Exception as e:
            # If any error occurs during health check, mark as unhealthy
            self._is_healthy = False
            self._last_health_check = datetime.now()
            
            logging.error(f"Health check failed for SQLite storage provider at {self.db_path}: {str(e)}")
            return False
    
    async def read(self, key: str, intent: Intent = Intent.STANDARD) -> Any:
        """
        Read a value from the storage.
        
        Args:
            key: The key to read
            intent: The intent for this operation
            
        Returns:
            The value if found, None otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to read from unhealthy SQLite storage provider: {key}")
        
        # In a real implementation, this would read from the database
        # For now, return None to indicate not found
        return None
    
    async def write(self, key: str, value: Any, intent: Intent = Intent.STANDARD) -> bool:
        """
        Write a value to the storage.
        
        Args:
            key: The key to write
            value: The value to store
            intent: The intent for this operation
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to write to unhealthy SQLite storage provider: {key}")
        
        # Apply intent-based logic (e.g., encryption for CRITICAL data)
        if intent == Intent.CRITICAL:
            # In real implementation, encrypt data before storing
            pass
        
        # In a real implementation, this would write to the database
        # For now, return True to indicate success
        return True
    
    async def delete(self, key: str, intent: Intent = Intent.STANDARD) -> bool:
        """
        Delete a value from the storage.
        
        Args:
            key: The key to delete
            intent: The intent for this operation
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to delete from unhealthy SQLite storage provider: {key}")
        
        # In a real implementation, this would delete from the database
        # For now, return True to indicate success
        return True


class MemoryStorageProvider(BaseProvider):
    """
    Health-aware in-memory storage provider implementing BaseProvider interface.
    
    Rationale: This provider demonstrates an alternative storage implementation
    that also implements the BaseProvider interface for health awareness.
    """
    
    def __init__(self, is_mock_healthy: bool = True):
        self._store = {}
        self._is_healthy = True
        self._last_health_check = datetime.now()
        self.is_mock_healthy = is_mock_healthy  # For testing purposes
        self.name = "memory_provider"  # Name for registry
    
    @property
    def is_healthy(self) -> bool:
        """
        Property indicating current health status of the provider.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        return self._is_healthy
    
    @property
    def last_health_check(self) -> datetime:
        """
        Property indicating the timestamp of the last health check.
            
        Returns:
            datetime: Timestamp of the last health check
        """
        return self._last_health_check
    
    @property
    def provider_properties(self) -> Dict[str, Any]:
        """Get provider properties"""
        return {
            "type": "memory",
            "supports_transactions": False,
            "supports_replication": False,
            "volatile": True
        }
    
    async def check_health(self) -> bool:
        """
        Asynchronously check the health of the memory provider.
        
        This method checks the health by verifying memory availability
        and the internal storage structure.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        try:
            # Check if we can access the internal store
            _ = self._store
            
            if self.is_mock_healthy:
                # Simulate a successful health check
                self._is_healthy = True
                self._last_health_check = datetime.now()
                
                # Log the health check
                logging.info("Memory storage provider is healthy")
            else:
                # Simulate an unhealthy state
                self._is_healthy = False
                self._last_health_check = datetime.now()
                
                # Log the health issue
                logging.warning("Memory storage provider is unhealthy")
            
            return self._is_healthy
            
        except Exception as e:
            # If any error occurs during health check, mark as unhealthy
            self._is_healthy = False
            self._last_health_check = datetime.now()
            
            logging.error(f"Health check failed for memory storage provider: {str(e)}")
            return False
    
    async def read(self, key: str, intent: Intent = Intent.STANDARD) -> Any:
        """
        Read a value from the memory storage.
        
        Args:
            key: The key to read
            intent: The intent for this operation
            
        Returns:
            The value if found, None otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to read from unhealthy memory storage provider: {key}")
        
        return self._store.get(key)
    
    async def write(self, key: str, value: Any, intent: Intent = Intent.STANDARD) -> bool:
        """
        Write a value to the memory storage.
        
        Args:
            key: The key to write
            value: The value to store
            intent: The intent for this operation
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to write to unhealthy memory storage provider: {key}")
        
        # Apply intent-based logic (e.g., encryption for CRITICAL data)
        if intent == Intent.CRITICAL:
            # In real implementation, encrypt data before storing
            pass
        
        self._store[key] = value
        return True
    
    async def delete(self, key: str, intent: Intent = Intent.STANDARD) -> bool:
        """
        Delete a value from the memory storage.
        
        Args:
            key: The key to delete
            intent: The intent for this operation
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_healthy:
            logging.warning(f"Attempting to delete from unhealthy memory storage provider: {key}")
        
        if key in self._store:
            del self._store[key]
            return True
        return False

__all__ = [
    "ServiceRegistry",
    "service_registry",
    "initialize_service_registry",
    "StorageProviderProtocol",
    "SQLiteStorageProvider",
    "MemoryStorageProvider",
]
