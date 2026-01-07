"""
EVOX Project Workflow Example
=============================

This example demonstrates the complete workflow of:
1. Creating a new project with `evo new project <name>`
2. Creating a new service within the project with `evo new service <name>`
3. Understanding the generated project structure
4. Working with the generated code

This example shows how to use the EVOX framework to create a complete microservice architecture.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

# Import core EVOX components
from evoid.core.application.project_manager import ProjectManager
from evoid.core.application.service_builder import ServiceBuilder
from evoid.core.communication.message_bus import message_bus
from evoid.core.data.data_io import data_io
from evoid.core.mapping.model_mapper import model_mapper
# Removed unused import - using utilities.serialization instead


async def demonstrate_project_creation():
    """
    Demonstrates the process of creating a new EVOX project.
    
    This function shows what happens behind the scenes when you run:
    `evo new project my_project`
    """
    print("=== EVOX Project Creation Workflow ===\n")
    
    # Create a sample project
    project_name = "my_microservice_project"
    project_dir = Path(f"./{project_name}")
    
    print(f"1. Creating project: {project_name}")
    print(f"2. Generating project structure at: {project_dir}")
    
    # Show the typical project structure that gets created
    project_structure = {
        project_name: {
            "__init__.py": "Package initialization",
            "main.py": "Main application entry point",
            "config.py": "Project configuration",
            "services/": {
                "__init__.py": "Services package",
                "README.md": "Service documentation"
            },
            "models/": {
                "__init__.py": "Data models package",
                "base.py": "Base model definitions"
            },
            "api/": {
                "__init__.py": "API package",
                "routes.py": "API route definitions"
            },
            "utils/": {
                "__init__.py": "Utility functions package",
                "helpers.py": "Helper functions"
            }
        }
    }
    
    print("\nGenerated Project Structure:")
    print_project_structure(project_structure)
    
    print("\n3. Project creation complete!")
    print("   You can now navigate to the project directory and start adding services.")


def print_project_structure(structure: Dict[str, Any], indent: int = 0):
    """Helper function to print project structure in a readable format."""
    for key, value in structure.items():
        print("  " * indent + f"├── {key}")
        if isinstance(value, dict):
            print_project_structure(value, indent + 1)
        elif isinstance(value, str):
            print("  " * (indent + 1) + f"// {value}")


async def demonstrate_service_creation():
    """
    Demonstrates the process of creating a new service within an EVOX project.
    
    This function shows what happens behind the scenes when you run:
    `evo new service user_service`
    """
    print("\n=== EVOX Service Creation Workflow ===\n")
    
    service_name = "user_service"
    project_name = "my_microservice_project"
    
    print(f"1. Creating service: {service_name}")
    print(f"2. Adding to project: {project_name}")
    
    # Show the service structure that gets created
    service_structure = {
        "services": {
            service_name: {
                "__init__.py": "Service package initialization",
                "main.py": "Service entry point and lifecycle management",
                "config.py": "Service-specific configuration",
                "models/": {
                    "__init__.py": "Service data models",
                    "user.py": "User model definition",
                    "schemas.py": "API schemas"
                },
                "api/": {
                    "__init__.py": "Service API package",
                    "routes.py": "Service API routes",
                    "endpoints.py": "Service endpoints"
                },
                "business/": {
                    "__init__.py": "Business logic package",
                    "user_service.py": "Core business logic",
                    "validation.py": "Business validation rules"
                },
                "data/": {
                    "__init__.py": "Data access package",
                    "repository.py": "Data access layer",
                    "queries.py": "Database queries"
                }
            }
        }
    }
    
    print("\nGenerated Service Structure:")
    print_project_structure(service_structure)
    
    print("\n3. Service creation complete!")
    print("   The service is now ready to be integrated with the main project.")


async def demonstrate_service_integration():
    """
    Demonstrates how services integrate with the main project.
    
    Shows how services communicate and share data within the EVOX ecosystem.
    """
    print("\n=== EVOX Service Integration ===\n")
    
    print("1. Service Registration:")
    print("   - Services are automatically registered with the main application")
    print("   - Service metadata is stored in the service registry")
    print("   - Health checks are set up for each service")
    
    print("\n2. Inter-Service Communication:")
    # Example of message bus usage between services
    async def user_service_handler(message):
        """Example handler for user service messages"""
        print(f"User service received: {message.payload}")
        return {"status": "processed", "data": message.payload}
    
    async def order_service_handler(message):
        """Example handler for order service messages"""
        print(f"Order service received: {message.payload}")
        return {"status": "processed", "data": message.payload}
    
    # Subscribe services to topics
    user_sub_id = message_bus.subscribe("user.events", user_service_handler)
    order_sub_id = message_bus.subscribe("order.events", order_service_handler)
    
    print(f"   - User service subscribed with ID: {user_sub_id}")
    print(f"   - Order service subscribed with ID: {order_sub_id}")
    
    print("\n3. Data Sharing:")
    # Example of data sharing between services
    await data_io.write("user_123", {"name": "John Doe", "email": "john@example.com"}, intent="CRITICAL")
    user_data = await data_io.read("user_123")
    print(f"   - Shared data: {user_data}")
    
    print("\n4. Service Discovery:")
    print("   - Services can discover each other through the service registry")
    print("   - Automatic load balancing between service instances")
    print("   - Health-aware routing")


async def demonstrate_complete_workflow():
    """
    Demonstrates the complete workflow from project creation to service deployment.
    """
    print("=== Complete EVOX Workflow Example ===\n")
    
    # Step 1: Create project
    await demonstrate_project_creation()
    
    # Step 2: Create service
    await demonstrate_service_creation()
    
    # Step 3: Integrate services
    await demonstrate_service_integration()
    
    print("\n=== Workflow Summary ===")
    print("1. evo new project <project_name>")
    print("   - Creates project structure")
    print("   - Sets up configuration")
    print("   - Initializes core components")
    
    print("\n2. evo new service <service_name>")
    print("   - Creates service structure within project")
    print("   - Sets up service-specific configuration")
    print("   - Integrates with main project")
    
    print("\n3. Service-to-Service Communication")
    print("   - Uses message bus for communication")
    print("   - Shares data through data_io")
    print("   - Maintains service isolation while enabling collaboration")
    
    print("\n4. Deployment")
    print("   - Each service can be deployed independently")
    print("   - Main project coordinates service orchestration")
    print("   - Automatic service discovery and registration")


async def main():
    """
    Main function to run the complete workflow example.
    """
    print("EVOX Complete Project Workflow Example")
    print("=" * 50)
    
    await demonstrate_complete_workflow()
    
    print("\n" + "=" * 50)
    print("Workflow example completed successfully!")
    print("\nKey Takeaways:")
    print("- EVOX provides a complete project scaffolding solution")
    print("- Services are created with full structure and integration")
    print("- Communication and data sharing are built-in")
    print("- Each service maintains its own lifecycle while being part of the ecosystem")


if __name__ == "__main__":
    asyncio.run(main())