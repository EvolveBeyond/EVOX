"""
Project Manager - Core component for managing EVOX projects and services

This module provides the core logic for project and service management,
including dependency resolution, status tracking, and service discovery.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import tomli
import tomli_w
from enum import Enum
import asyncio


class ProjectStatus(Enum):
    """Status of a project"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CORRUPT = "corrupt"


class ServiceStatus(Enum):
    """Status of a service"""
    INSTALLED = "installed"
    MISSING_DEPS = "missing_deps"
    INACTIVE = "inactive"


class ProjectManager:
    """
    Project Manager - Core logic for managing EVOX projects and services
    
    Handles project creation, service management, and dependency resolution
    without any CLI-specific logic.
    """
    
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self._config_cache: Dict[str, Any] = {}
    
    def create_project(self, name: str, project_path: Path | None = None) -> bool:
        """
        Create a new EVOX project with the specified name.
        
        Args:
            name: Name of the project
            project_path: Path where the project should be created (defaults to current directory)
            
        Returns:
            True if project was created successfully, False otherwise
        """
        target_path = project_path or Path.cwd() / name
        
        if target_path.exists():
            print(f"Project directory '{target_path}' already exists!")
            return False
        
        # Create project structure
        target_path.mkdir(parents=True)
        
        # Create basic project files
        (target_path / "services").mkdir()
        (target_path / "plugins").mkdir()
        
        # Create pyproject.toml with Rye configuration
        pyproject_content = f'''[project]
name = "{name}"
version = "0.1.0"
description = "EVOID microservices project - Rye-Native"
authors = [
    {{ name = "Developer", email = "dev@example.com" }}
]
dependencies = [
    "evoid>=0.2.3_Beta",
]
requires-python = ">= 3.11"
readme = "README.md"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.rye]
managed = true
dev-dependencies = [
    "pytest>=7.0.0,<8.0.0",
    "httpx>=0.25.0,<0.26.0",
    "black>=23.0.0,<24.0.0",
    "isort>=5.12.0,<6.0.0",
]

[tool.hatch.metadata]
allow-direct-references = true

[tool.hatch.build.targets.wheel]
packages = ["services", "plugins"]

[project.scripts]

[tool.rye.scripts]
dev = "evo run --dev"
health = "evo health"
test = "evo test"
'''
        
        (target_path / "pyproject.toml").write_text(pyproject_content)
        (target_path / ".env.example").write_text("# Environment variables\n")
        (target_path / "README.md").write_text(f"# {name}\n\nEVOID project created with `evo new {name}`\n")
        
        # Create config.toml
        config_content = '''# EVOID Project Configuration

[project]
name = "default"
version = "0.2.3_Beta"
description = "EVOID microservices project"

# Priority Queue Configuration
[queue]
# Concurrency limits per priority level
[queue.concurrency_limits]
high = 10
medium = 5
low = 2

# Queue length limits per priority level
[queue.queue_limits]
high = 50
medium = 100
low = 200

# Caching Configuration
[caching]
default_ttl = 300  # 5 minutes
enable_fallback = true
max_stale_on_error = 3600  # 1 hour

[caching.aggressive_fallback]
enabled = false
max_stale_duration = "24h"

# Storage Configuration
[storage]
backend = "memory"  # memory, sqlite

[storage.sqlite]
path = "data.db"
'''
        
        (target_path / "config.toml").write_text(config_content)
        
        return True
    
    def create_service(self, name: str, services_path: Path | None = None) -> bool:
        """
        Create a new EVOID service with the specified name.
        
        Args:
            name: Name of the service
            services_path: Path to the services directory (defaults to project services dir)
            
        Returns:
            True if service was created successfully, False otherwise
        """
        services_path = services_path or self.project_root / "services"
        service_path = services_path / name
        
        if not services_path.exists():
            print(f"Error: Services directory '{services_path}' not found.")
            return False
        
        if service_path.exists():
            print(f"Service directory '{name}' already exists!")
            return False
        
        # Create service structure
        service_path.mkdir(parents=True)
        
        # Create service template
        main_py_content = f'''"""
{name} Service - Generated by EVOID
"""

from evoid import service, get, post, delete, Param, Query, Body, Intent, auth, data_io

svc = service("{name}") \\
    .port(8000) \\
    .build()

@get("/hello")
async def hello():
    return {{"message": "Hello from {name} service!"}}

if __name__ == "__main__":
    svc.run(dev=True)
'''
        
        (service_path / "main.py").write_text(main_py_content)
        
        # Create config.toml
        config_content = f'''# {name} Service Configuration

[service]
name = "{name}"
port = 8000

[storage]
backend = "memory"

[caching]
default_ttl = 300
enable_fallback = true
'''
        
        (service_path / "config.toml").write_text(config_content)
        
        return True
    
    def get_project_status(self) -> ProjectStatus:
        """
        Get the status of the current project.
        
        Returns:
            ProjectStatus indicating the state of the project
        """
        if not (self.project_root / "pyproject.toml").exists():
            return ProjectStatus.CORRUPT
        
        if not (self.project_root / "services").exists():
            return ProjectStatus.INACTIVE
        
        return ProjectStatus.ACTIVE
    
    def list_services(self) -> List[Dict[str, Any]]:
        """
        List all services in the project.
        
        Returns:
            List of service information dictionaries
        """
        services_path = self.project_root / "services"
        if not services_path.exists():
            return []
        
        services = []
        for service_dir in services_path.iterdir():
            if service_dir.is_dir():
                config_path = service_dir / "config.toml"
                config = {}
                
                if config_path.exists():
                    try:
                        with open(config_path, "rb") as f:
                            config = tomli.load(f)
                    except Exception:
                        pass  # Config file is malformed or doesn't exist
                
                service_info = {
                    "name": service_dir.name,
                    "path": str(service_dir),
                    "config": config,
                    "status": self._get_service_status(service_dir.name)
                }
                services.append(service_info)
        
        return services
    
    def _get_service_status(self, service_name: str) -> ServiceStatus:
        """
        Determine the status of a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ServiceStatus indicating the state of the service
        """
        # Check if service directory exists
        service_path = self.project_root / "services" / service_name
        if not service_path.exists():
            return ServiceStatus.INACTIVE
        
        # Check if config exists
        config_path = service_path / "config.toml"
        if not config_path.exists():
            return ServiceStatus.INACTIVE
        
        # Check dependencies by trying to import the service
        try:
            # Add service path to Python path temporarily
            service_path_str = str(service_path.absolute())
            if service_path_str not in sys.path:
                sys.path.insert(0, service_path_str)
            
            # Try to import the main module
            import importlib.util
            main_py = service_path / "main.py"
            if main_py.exists():
                spec = importlib.util.spec_from_file_location(f"{service_name}_module", main_py)
                module = importlib.util.module_from_spec(spec)
                # Don't execute to avoid side effects, just check if it can be parsed
                spec.loader.exec_module(module)
            
            # Remove path from sys.path
            if service_path_str in sys.path:
                sys.path.remove(service_path_str)
                
            return ServiceStatus.INSTALLED
        except ImportError:
            return ServiceStatus.MISSING_DEPS
        except Exception:
            return ServiceStatus.INACTIVE


# Global project manager instance
_project_manager: ProjectManager | None = None


def get_project_manager() -> ProjectManager:
    """
    Get the global project manager instance.
    
    Returns:
        ProjectManager instance
    """
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager


__all__ = [
    "ProjectManager",
    "ProjectStatus",
    "ServiceStatus",
    "get_project_manager"
]