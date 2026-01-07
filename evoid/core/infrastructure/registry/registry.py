"""
Registry-Driven Service Registry - Intent-Aware, Pluggable Service Discovery

This module provides a Registry-Driven service registry that allows EVOX to discover services 
and manage their dependencies using `rye`. It implements automatic scanning 
of the pluggable_services directory and uses config.toml files to identify 
service capabilities and prerequisites.

The Intent-Aware registry supports:
1. Automatic scanning of pluggable services
2. Dependency resolution for ordered loading
3. Rye-aware synchronization
4. Single source of truth for loaded modules
"""

import asyncio
import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Set
import tomli
from dataclasses import dataclass


@dataclass
class ServiceInfo:
    """Information about a registered service"""
    name: str
    path: Path
    config: dict[str, Any]
    capabilities: list[str]
    prerequisites: list[str]
    loaded: bool = False
    module: Any | None = None


class ServiceRegistry:
    """
    Service Registry - Plug & Play registry system for EVOX
    
    Automatically scans the pluggable_services directory and uses config.toml
    to identify service capabilities and prerequisites.
    """
    
    def __init__(self, services_dir: Path | None = None):
        self._services: dict[str, ServiceInfo] = {}
        self._services_dir = services_dir or Path(__file__).parent.parent / "pluggable_services"
        
    def scan_services(self) -> dict[str, ServiceInfo]:
        """
        Scan the pluggable_services directory to discover available services.
        
        Returns:
            Dictionary mapping service names to their ServiceInfo objects
        """
        if not self._services_dir.exists():
            return {}
        
        for service_path in self._services_dir.iterdir():
            if service_path.is_dir() and (service_path / "config.toml").exists():
                self._load_service_config(service_path)
        
        return self._services
    
    def _load_service_config(self, service_path: Path):
        """Load configuration for a service from its config.toml file"""
        config_path = service_path / "config.toml"
        
        try:
            with open(config_path, "rb") as f:
                config = tomli.load(f)
        except Exception as e:
            print(f"Warning: Could not load config.toml for service at {service_path}: {e}")
            return
        
        # Extract service name from config or directory name
        service_name = config.get("service", {}).get("name") or service_path.name.replace("_", "-")
        
        # Extract capabilities and prerequisites
        capabilities = config.get("service", {}).get("capabilities", [])
        if not capabilities:
            # Default capabilities based on directory structure and common patterns
            if "data_intent" in service_path.name.lower():
                capabilities = ["data-intent", "storage"]
            elif "management" in service_path.name.lower():
                capabilities = ["service-management", "discovery"]
            else:
                capabilities = ["generic-service"]
        
        prerequisites = config.get("service", {}).get("prerequisites", [])
        
        service_info = ServiceInfo(
            name=service_name,
            path=service_path,
            config=config,
            capabilities=capabilities,
            prerequisites=prerequisites
        )
        
        self._services[service_name] = service_info
    
    def get_service(self, service_name: str) -> ServiceInfo | None:
        """Get information about a specific service"""
        return self._services.get(service_name)
    
    def get_all_services(self) -> dict[str, ServiceInfo]:
        """Get all registered services"""
        return self._services.copy()
    
    def get_services_by_capability(self, capability: str) -> list[ServiceInfo]:
        """Get all services that provide a specific capability"""
        return [service for service in self._services.values() 
                if capability in service.capabilities]
    
    def resolve_dependencies(self) -> list[str]:
        """
        Resolve service dependencies and return the order in which services should be loaded.
        
        Uses topological sorting to determine the correct loading order based on prerequisites.
        
        Returns:
            List of service names in the order they should be loaded
        """
        # Build dependency graph
        graph = {}
        all_services = set(self._services.keys())
        
        for service_name, service_info in self._services.items():
            graph[service_name] = set(service_info.prerequisites) & all_services
        
        # Perform topological sort
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                raise ValueError(f"Circular dependency detected involving {node}")
            if node in visited:
                return
            
            temp_visited.add(node)
            for dependency in graph.get(node, []):
                visit(dependency)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for service_name in self._services:
            if service_name not in visited:
                visit(service_name)
        
        return result
    
    def load_service(self, service_name: str) -> Any | None:
        """
        Load a service module by name.
        
        Args:
            service_name: Name of the service to load
            
        Returns:
            The loaded service module or None if loading failed
        """
        service_info = self._services.get(service_name)
        if not service_info:
            return None
        
        if service_info.loaded and service_info.module:
            return service_info.module
        
        try:
            # Add service path to Python path temporarily
            service_path = str(service_info.path.absolute())
            if service_path not in sys.path:
                sys.path.insert(0, service_path)
            
            # Import the main module
            module_name = f"{service_name.replace('-', '_')}_service"
            main_py = service_info.path / "main.py"
            
            if main_py.exists():
                # Import using importlib
                spec = importlib.util.spec_from_file_location(module_name, main_py)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                service_info.module = module
                service_info.loaded = True
                
                # Remove path from sys.path
                if service_path in sys.path:
                    sys.path.remove(service_path)
                
                return module
        except Exception as e:
            print(f"Error loading service {service_name}: {e}")
            # Remove path from sys.path in case of error
            service_path = str(service_info.path.absolute())
            if service_path in sys.path:
                sys.path.remove(service_path)
            return None
    
    def load_all_services(self) -> dict[str, Any]:
        """
        Load all services in the correct dependency order.
        
        Returns:
            Dictionary mapping service names to their loaded modules
        """
        service_order = self.resolve_dependencies()
        loaded_services = {}
        
        for service_name in service_order:
            module = self.load_service(service_name)
            if module:
                loaded_services[service_name] = module
        
        return loaded_services
    
    def check_rye_requirements(self, service_name: str) -> bool:
        """
        Check if the current Python environment has the necessary extras 
        installed via rye for a specific pluggable service.
        
        Args:
            service_name: Name of the service to check requirements for
            
        Returns:
            True if all requirements are satisfied, False otherwise
        """
        service_info = self._services.get(service_name)
        if not service_info:
            return False
        
        # Get requirements from config
        requirements = service_info.config.get("service", {}).get("requirements", [])
        
        # Check if rye is available
        try:
            result = subprocess.run(["rye", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            has_rye = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            has_rye = False
        
        if not has_rye:
            print("Warning: rye not found in the system")
            return False
        
        # Check if requirements are installed
        for req in requirements:
            try:
                # Use pip list to check if package is installed
                result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                                      capture_output=True, text=True, timeout=10)
                installed_packages = result.stdout.lower()
                
                if req.lower() not in installed_packages:
                    return False
            except (subprocess.TimeoutExpired, Exception):
                return False
        
        return True
    
    def sync_rye_requirements(self, service_name: str) -> bool:
        """
        Synchronize the Python environment with the necessary extras 
        installed via rye for a specific pluggable service.
        
        Args:
            service_name: Name of the service to sync requirements for
            
        Returns:
            True if synchronization was successful, False otherwise
        """
        service_info = self._services.get(service_name)
        if not service_info:
            return False
        
        # Get requirements from config
        requirements = service_info.config.get("service", {}).get("requirements", [])
        
        if not requirements:
            # If no specific requirements, just run rye sync
            try:
                result = subprocess.run(["rye", "sync"], 
                                      capture_output=True, text=True, timeout=30)
                return result.returncode == 0
            except (subprocess.TimeoutExpired, Exception) as e:
                print(f"Error running 'rye sync': {e}")
                return False
        
        # Install specific requirements
        try:
            for req in requirements:
                result = subprocess.run(["rye", "add", req], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    print(f"Error adding requirement {req}: {result.stderr}")
                    return False
            
            # Run sync to update the environment
            result = subprocess.run(["rye", "sync"], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"Error syncing requirements: {e}")
            return False


# Global service registry instance
_registry: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    """
    Get the global service registry instance.
    
    Returns:
        ServiceRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
        _registry.scan_services()
    return _registry


def register_service(service_name: str, service_info: ServiceInfo):
    """
    Register a service with the global registry.
    
    Args:
        service_name: Name of the service
        service_info: ServiceInfo object with service details
    """
    registry = get_service_registry()
    registry._services[service_name] = service_info


def get_service(service_name: str) -> ServiceInfo | None:
    """
    Get information about a specific service from the global registry.
    
    Args:
        service_name: Name of the service to get
        
    Returns:
        ServiceInfo object or None if service not found
    """
    registry = get_service_registry()
    return registry.get_service(service_name)


def load_service_module(service_name: str) -> Any | None:
    """
    Load a service module from the global registry.
    
    Args:
        service_name: Name of the service to load
        
    Returns:
        Loaded module or None if loading failed
    """
    registry = get_service_registry()
    return registry.load_service(service_name)


def get_services_by_capability(capability: str) -> list[ServiceInfo]:
    """
    Get all services that provide a specific capability from the global registry.
    
    Args:
        capability: Capability to search for
        
    Returns:
        List of ServiceInfo objects that provide the capability
    """
    registry = get_service_registry()
    return registry.get_services_by_capability(capability)


def resolve_service_dependencies() -> list[str]:
    """
    Resolve service dependencies and return the loading order from the global registry.
    
    Returns:
        List of service names in the order they should be loaded
    """
    registry = get_service_registry()
    return registry.resolve_dependencies()


def load_all_services() -> dict[str, Any]:
    """
    Load all services in the correct dependency order from the global registry.
    
    Returns:
        Dictionary mapping service names to their loaded modules
    """
    registry = get_service_registry()
    return registry.load_all_services()


__all__ = [
    "ServiceRegistry",
    "ServiceInfo",
    "get_service_registry",
    "register_service", 
    "get_service",
    "load_service_module",
    "get_services_by_capability",
    "resolve_service_dependencies",
    "load_all_services"
]