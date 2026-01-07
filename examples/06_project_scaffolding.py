"""
EVOX Project Structure Generator
================================

This script demonstrates how to create a complete EVOX microservice project structure.
It shows the recommended directory layout and file organization for production projects.

Features demonstrated:
- Complete project scaffolding
- Multi-service architecture setup
- Configuration management
- Shared components structure
- Deployment configurations
- Development workflows
"""

import os
from pathlib import Path
from typing import Dict, List


class ProjectStructureGenerator:
    """Generate complete EVOX project structure"""
    
    def __init__(self, project_name: str, root_path: str = "."):
        self.project_name = project_name
        self.root_path = Path(root_path) / project_name
        self.services = []
    
    def add_service(self, name: str, port: int, description: str = ""):
        """Add a service to the project"""
        self.services.append({
            "name": name,
            "port": port,
            "description": description
        })
    
    def generate_structure(self) -> Dict[str, List[str]]:
        """Generate the complete project structure"""
        
        structure = {
            # Root level files
            "root": [
                "README.md",
                "pyproject.toml",
                "requirements.txt",
                "docker-compose.yml",
                ".gitignore",
                ".env.example",
                "Makefile"
            ],
            
            # Documentation
            "docs": [
                "architecture.md",
                "api-reference.md",
                "deployment-guide.md",
                "development-setup.md"
            ],
            
            # Shared libraries
            "shared": [
                "__init__.py",
                "models.py",
                "exceptions.py",
                "utils.py",
                "constants.py"
            ],
            
            # Configuration
            "config": [
                "base.toml",
                "development.toml",
                "staging.toml",
                "production.toml"
            ],
            
            # Infrastructure
            "infrastructure": [
                "docker/",
                "kubernetes/",
                "terraform/",
                "scripts/"
            ],
            
            # Tests
            "tests": [
                "unit/",
                "integration/",
                "e2e/",
                "fixtures/",
                "conftest.py"
            ]
        }
        
        return structure
    
    def create_service_structure(self, service_name: str) -> Dict[str, List[str]]:
        """Create structure for individual service"""
        return {
            service_name: [
                "__init__.py",
                "main.py",
                "config.toml",
                "Dockerfile",
                "requirements.txt",
                "controllers/",
                "models/",
                "services/",
                "repositories/",
                "middleware/",
                "utils/"
            ]
        }
    
    def generate_complete_project(self):
        """Generate complete project with all services"""
        print(f"🏗️  Generating EVOX project structure for '{self.project_name}'")
        print("=" * 50)
        
        # Create root directory
        self.root_path.mkdir(exist_ok=True)
        
        # Generate base structure
        structure = self.generate_structure()
        
        # Create directories and files
        for category, files in structure.items():
            if category == "root":
                # Root level files
                for file in files:
                    filepath = self.root_path / file
                    if file.endswith('/'):
                        filepath.mkdir(exist_ok=True)
                    else:
                        filepath.touch()
                        print(f"📄 Created: {filepath.relative_to(self.root_path.parent)}")
            else:
                # Category directories
                dir_path = self.root_path / category
                dir_path.mkdir(exist_ok=True)
                print(f"📁 Created directory: {dir_path.relative_to(self.root_path.parent)}")
                
                for file in files:
                    filepath = dir_path / file
                    if file.endswith('/'):
                        filepath.mkdir(exist_ok=True)
                    else:
                        filepath.touch()
                    print(f"   📄 {filepath.relative_to(self.root_path.parent)}")
        
        # Create services
        print(f"\n🔧 Creating {len(self.services)} services:")
        for service in self.services:
            service_struct = self.create_service_structure(service["name"])
            service_path = self.root_path / "services" / service["name"]
            service_path.mkdir(parents=True, exist_ok=True)
            
            for category, files in service_struct.items():
                for file in files:
                    filepath = service_path / file
                    if file.endswith('/'):
                        filepath.mkdir(exist_ok=True)
                    else:
                        filepath.touch()
                    print(f"      📄 {filepath.relative_to(self.root_path.parent)}")
            
            # Create service main.py template
            self._create_service_main(service_path, service)
            # Create service config
            self._create_service_config(service_path, service)
        
        print(f"\n✅ Project structure generated successfully!")
        print(f"📂 Location: {self.root_path.absolute()}")
        return self.root_path
    
    def _create_service_main(self, service_path: Path, service: Dict):
        """Create main.py template for service"""
        main_content = f'''"""
{service["name"].title()} Service
{service["description"] or "Microservice for " + service["name"].replace("-", " ").title()}
"""

from evoid import service, get, post, Controller
from pydantic import BaseModel
from typing import Dict, Any


class HealthResponse(BaseModel):
    status: str
    service: str
    port: int


@get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="{service["name"]}",
        port={service["port"]}
    )


# Create service
app = service("{service["name"]}").port({service["port"]}).build()


if __name__ == "__main__":
    print(f"🚀 Starting {{service["name"]}} service on port {service["port"]}")
    # Uncomment to run: app.run()
'''
        
        (service_path / "main.py").write_text(main_content.strip())
    
    def _create_service_config(self, service_path: Path, service: Dict):
        """Create config.toml for service"""
        config_content = f'''# {service["name"].title()} Service Configuration

[service]
name = "{service["name"]}"
version = "1.0.0"
port = {service["port"]}

[database]
url = "sqlite:///data/{service["name"]}.db"
pool_size = 10

[cache]
redis_url = "redis://localhost:6379"
ttl_default = 300

[logging]
level = "INFO"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

[messaging]
broker_url = "redis://localhost:6379"
exchange = "{service["name"]}_events"
'''
        
        (service_path / "config.toml").write_text(config_content.strip())


# Example usage
if __name__ == "__main__":
    # Create a sample e-commerce microservice system
    generator = ProjectStructureGenerator("ecommerce-platform")
    
    # Add services
    generator.add_service("user-service", 8001, "User management and authentication")
    generator.add_service("product-service", 8002, "Product catalog and inventory")
    generator.add_service("order-service", 8003, "Order processing and management")
    generator.add_service("payment-service", 8004, "Payment processing")
    generator.add_service("notification-service", 8005, "Email and SMS notifications")
    generator.add_service("api-gateway", 8000, "API gateway and load balancing")
    
    # Generate the complete project
    project_path = generator.generate_complete_project()
    
    print(f"\n🚀 Generated microservice project structure!")
    print(f"📋 Services created:")
    for service in generator.services:
        print(f"   • {service['name']} (port {service['port']})")
    
    print(f"\n🔧 Next steps:")
    print(f"1. cd {project_path}")
    print(f"2. Review the generated structure")
    print(f"3. Customize configs in config/ directory")
    print(f"4. Implement service logic in services/*/main.py")
    print(f"5. Run individual services or use docker-compose")