"""
EVOX Docker Compose Deployment Example
=====================================

This example demonstrates a complete production-like deployment using Docker Compose,
showing how to orchestrate multiple EVOX microservices with their dependencies.

Features demonstrated:
- Multi-service Docker Compose setup
- Service dependencies (Redis, PostgreSQL)
- Load balancing with nginx
- Monitoring stack (Prometheus, Grafana)
- Logging aggregation
- Health checks and restart policies
- Environment configuration
- Volume management
"""

from typing import Dict, List
import yaml


class DockerComposeGenerator:
    """Generate production-ready Docker Compose configuration"""
    
    def __init__(self, project_name: str = "evoid-platform"): 
        self.project_name = project_name
        self.services = {}
        self.networks = ["backend", "frontend", "monitoring"]
        self.volumes = ["postgres-data", "redis-data", "grafana-storage"]
    
    def add_evox_service(self, name: str, port: int, depends_on: List[str] = None): # Kept for backward compatibility, use add_evoid_service instead
        """Add EVOX service to compose file"""
        self.services[name] = {
            "build": f"./services/{name}",
            "ports": [f"{port}:{port}"],
            "environment": [
                f"SERVICE_PORT={port}",
                f"SERVICE_NAME={name}",
                "DATABASE_URL=postgresql://postgres:password@postgres:5432/evoid",
                "REDIS_URL=redis://redis:6379",
                "LOG_LEVEL=INFO"
            ],
            "depends_on": depends_on or [],
            "networks": ["backend"],
            "restart": "unless-stopped",
            "healthcheck": {
                "test": ["CMD", "curl", "-f", f"http://localhost:{port}/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "40s"
            },
            "volumes": [
                f"./services/{name}:/app",
                "./logs:/app/logs"
            ]
        }
    
    def add_infrastructure_service(self, name: str, image: str, config: Dict):
        """Add infrastructure service (DB, cache, monitoring)"""
        self.services[name] = config
    
    def generate_compose_dict(self) -> Dict:
        """Generate complete docker-compose dictionary"""
        compose = {
            "version": "3.8",
            "services": self.services,
            "networks": {net: {"driver": "bridge"} for net in self.networks},
            "volumes": {vol: {} for vol in self.volumes}
        }
        return compose
    
    def save_compose_file(self, filename: str = "docker-compose.yml"):
        """Save docker-compose.yml file"""
        compose_dict = self.generate_compose_dict()
        with open(filename, 'w') as f:
            yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)
        print(f"💾 Docker Compose file saved as {filename}")


# Generate complete deployment setup
def create_production_deployment():
    """Create complete production deployment configuration"""
    
    generator = DockerComposeGenerator("evoid-microservices")
    
    # Add infrastructure services
    generator.add_infrastructure_service(
        "postgres",
        "postgres:15",
        {
            "environment": [
                "POSTGRES_DB=evoid",
                "POSTGRES_USER=postgres",
                "POSTGRES_PASSWORD=password"
            ],
            "volumes": [
                "postgres-data:/var/lib/postgresql/data",
                "./init-scripts:/docker-entrypoint-initdb.d"
            ],
            "ports": ["5432:5432"],
            "networks": ["backend"],
            "restart": "unless-stopped",
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U postgres"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3
            }
        }
    )
    
    generator.add_infrastructure_service(
        "redis",
        "redis:7-alpine",
        {
            "volumes": ["redis-data:/data"],
            "ports": ["6379:6379"],
            "networks": ["backend"],
            "restart": "unless-stopped",
            "command": "redis-server --appendonly yes",
            "healthcheck": {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3
            }
        }
    )
    
    # Add nginx load balancer
    generator.add_infrastructure_service(
        "nginx",
        "nginx:alpine",
        {
            "ports": ["80:80", "443:443"],
            "volumes": [
                "./nginx/nginx.conf:/etc/nginx/nginx.conf",
                "./nginx/conf.d:/etc/nginx/conf.d",
                "./certs:/etc/nginx/certs"
            ],
            "depends_on": [
                "api-gateway",
                "user-service",
                "product-service"
            ],
            "networks": ["frontend", "backend"],
            "restart": "unless-stopped"
        }
    )
    
    # Add monitoring services
    generator.add_infrastructure_service(
        "prometheus",
        "prom/prometheus",
        {
            "volumes": [
                "./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml",
                "./prometheus/rules:/etc/prometheus/rules"
            ],
            "ports": ["9090:9090"],
            "networks": ["monitoring"],
            "restart": "unless-stopped"
        }
    )
    
    generator.add_infrastructure_service(
        "grafana",
        "grafana/grafana",
        {
            "environment": [
                "GF_SECURITY_ADMIN_USER=admin",
                "GF_SECURITY_ADMIN_PASSWORD=admin"
            ],
            "volumes": [
                "grafana-storage:/var/lib/grafana",
                "./grafana/dashboards:/etc/grafana/provisioning/dashboards",
                "./grafana/datasources:/etc/grafana/provisioning/datasources"
            ],
            "ports": ["3000:3000"],
            "networks": ["monitoring"],
            "restart": "unless-stopped",
            "depends_on": ["prometheus"]
        }
    )
    
    # Add EVOX microservices
    generator.add_evox_service("api-gateway", 8000, ["user-service", "product-service"]) # For compatibility
    generator.add_evox_service("user-service", 8001, ["postgres", "redis"]) # For compatibility
    generator.add_evox_service("product-service", 8002, ["postgres", "redis"]) # For compatibility
    generator.add_evox_service("order-service", 8003, ["postgres", "redis"]) # For compatibility
    generator.add_evox_service("payment-service", 8004, ["postgres", "redis"]) # For compatibility
    generator.add_evox_service("notification-service", 8005, ["redis"]) # For compatibility
    
    return generator


# Example usage
if __name__ == "__main__":
    print("🐳 EVOX Docker Compose Deployment Generator")
    print("=" * 45)
    
    # Create deployment
    deployment = create_production_deployment()
    
    # Save configuration
    deployment.save_compose_file("docker-compose.production.yml")
    
    print("\n📋 Generated deployment includes:")
    print("🌐 Frontend Network: nginx load balancer")
    print("🔧 Backend Network: microservices and databases")
    print("📊 Monitoring Network: Prometheus and Grafana")
    print("\n📦 Services:")
    for service_name in deployment.services.keys():
        print(f"   • {service_name}")
    
    print("\n🚀 Deployment Commands:")
    print("1. docker-compose -f docker-compose.production.yml up -d")
    print("2. docker-compose -f docker-compose.production.yml ps")
    print("3. docker-compose -f docker-compose.production.yml logs -f")
    print("4. docker-compose -f docker-compose.production.yml down")
    
    print("\n🔗 Access Points:")
    print("   • Application: http://localhost")
    print("   • API Gateway: http://localhost:8000")
    print("   • Grafana: http://localhost:3000 (admin/admin)")
    print("   • Prometheus: http://localhost:9090")