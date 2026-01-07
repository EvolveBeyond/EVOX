"""
Service Management Service - Pluggable Core Service

This service demonstrates:
- Pluggable service architecture
- Type-safe dependency injection
- Service discovery and management
- Environmental intelligence integration
"""

from evoid import service, get, post, put, delete, Param, Body, Intent
from evoid.core.inject import inject
from evoid.core.intelligence import get_environmental_intelligence
from pydantic import BaseModel
from typing import Annotated, Optional, Dict, Any, List
import asyncio

# Define data models for service management
class ServiceRegistration(BaseModel):
    """Registration information for a service"""
    name: str
    host: str
    port: int
    status: str = "active"  # active, inactive, maintenance
    version: str = "1.0.0"
    tags: List[str] = []

class ServiceUpdateRequest(BaseModel):
    """Request to update service registration"""
    host: Optional[str] = None
    port: Optional[int] = None
    status: Optional[str] = None
    version: Optional[str] = None
    tags: Optional[List[str]] = None

class ServiceHealthCheck(BaseModel):
    """Health check result for a service"""
    name: str
    status: str  # healthy, unhealthy, degraded
    response_time_ms: float
    last_checked: str
    details: Dict[str, Any] = {}

# In-memory storage for service registrations
services_db: Dict[str, ServiceRegistration] = {}

# Create service with type-safe registration
svc = service("service-management-service").port(8005).build()

# Type-safe dependency injection examples
class ServiceManagementService:
    """Service for managing service registrations"""
    
    async def get_service(self, service_name: str) -> Optional[ServiceRegistration]:
        """Get a service registration by name"""
        return services_db.get(service_name)
    
    async def register_service(self, service: ServiceRegistration) -> ServiceRegistration:
        """Register a new service"""
        services_db[service.name] = service
        return service
    
    async def update_service(self, service_name: str, updates: ServiceUpdateRequest) -> Optional[ServiceRegistration]:
        """Update an existing service registration"""
        if service_name not in services_db:
            return None
        
        service = services_db[service_name]
        
        # Apply updates
        if updates.host is not None:
            service.host = updates.host
        if updates.port is not None:
            service.port = updates.port
        if updates.status is not None:
            service.status = updates.status
        if updates.version is not None:
            service.version = updates.version
        if updates.tags is not None:
            service.tags = updates.tags
        
        services_db[service_name] = service
        return service
    
    async def unregister_service(self, service_name: str) -> bool:
        """Unregister a service"""
        if service_name in services_db:
            del services_db[service_name]
            return True
        return False
    
    async def list_services(self) -> Dict[str, ServiceRegistration]:
        """List all service registrations"""
        return services_db.copy()
    
    async def health_check_service(self, service_name: str) -> ServiceHealthCheck:
        """Perform a health check on a service"""
        service = services_db.get(service_name)
        if not service:
            return ServiceHealthCheck(
                name=service_name,
                status="unregistered",
                response_time_ms=0,
                last_checked="now"
            )
        
        # Simulate health check (in real implementation, this would make HTTP calls)
        import time
        start_time = time.time()
        
        # Mock health check logic
        if service.status == "inactive":
            status = "unhealthy"
        elif service.status == "maintenance":
            status = "degraded"
        else:
            status = "healthy"
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return ServiceHealthCheck(
            name=service_name,
            status=status,
            response_time_ms=response_time,
            last_checked="now"
        )

# GET endpoint to retrieve a service registration
@get("/services/{service_name}")
@Intent(cacheable=True, ttl=300)  # Cacheable with 5-minute TTL
async def get_service(service_name: Annotated[str, Param]):
    """Retrieve a service registration by name"""
    # Type-safe dependency injection
    svc_mgmt = inject(ServiceManagementService)
    service = await svc_mgmt.get_service(service_name)
    
    if service:
        return service
    else:
        return {"error": "Service not found"}, 404

# POST endpoint to register a new service
@post("/services")
@Intent(consistency="strong")  # Strong consistency for registration
async def register_service(service_data: Annotated[ServiceRegistration, Body]):
    """Register a new service"""
    # Type-safe dependency injection
    svc_mgmt = inject(ServiceManagementService)
    
    # Check if service already exists
    existing = await svc_mgmt.get_service(service_data.name)
    if existing:
        return {"error": "Service already registered"}, 409
    
    registered_service = await svc_mgmt.register_service(service_data)
    return {"message": "Service registered", "service": registered_service}, 201

# PUT endpoint to update an existing service registration
@put("/services/{service_name}")
@Intent(consistency="strong")  # Strong consistency for updates
async def update_service(
    service_name: Annotated[str, Param], 
    update_data: Annotated[ServiceUpdateRequest, Body]
):
    """Update an existing service registration"""
    # Type-safe dependency injection
    svc_mgmt = inject(ServiceManagementService)
    
    updated_service = await svc_mgmt.update_service(service_name, update_data)
    if updated_service:
        return {"message": "Service updated", "service": updated_service}
    else:
        return {"error": "Service not found"}, 404

# DELETE endpoint to unregister a service
@delete("/services/{service_name}")
@Intent(consistency="strong")  # Strong consistency for unregistration
async def unregister_service(service_name: Annotated[str, Param]):
    """Unregister a service"""
    # Type-safe dependency injection
    svc_mgmt = inject(ServiceManagementService)
    
    success = await svc_mgmt.unregister_service(service_name)
    if success:
        return {"message": "Service unregistered"}
    else:
        return {"error": "Service not found"}, 404

# GET endpoint to list all service registrations
@get("/services")
@Intent(cacheable=True, ttl=120)  # Cacheable with 2-minute TTL
async def list_services():
    """List all service registrations"""
    # Type-safe dependency injection
    svc_mgmt = inject(ServiceManagementService)
    services = await svc_mgmt.list_services()
    return {"services": services, "count": len(services)}

# GET endpoint to perform health check on a service
@get("/services/{service_name}/health")
@Intent(cacheable=True, ttl=30)  # Cacheable with 30-second TTL
async def health_check_service(service_name: Annotated[str, Param]):
    """Perform health check on a service"""
    # Type-safe dependency injection
    svc_mgmt = inject(ServiceManagementService)
    health_check = await svc_mgmt.health_check_service(service_name)
    return health_check

# GET endpoint to get overall system health
@get("/health/overview")
@Intent(cacheable=True, ttl=30)  # Cacheable with 30-second TTL
async def system_health_overview():
    """Get overall system health overview"""
    # Type-safe dependency injection
    svc_mgmt = inject(ServiceManagementService)
    services = await svc_mgmt.list_services()
    
    # Perform health checks on all services
    health_checks = []
    healthy_count = 0
    unhealthy_count = 0
    
    for service_name in services.keys():
        health_check = await svc_mgmt.health_check_service(service_name)
        health_checks.append(health_check)
        
        if health_check.status == "healthy":
            healthy_count += 1
        elif health_check.status == "unhealthy":
            unhealthy_count += 1
    
    # Get environmental intelligence
    env_intel = get_environmental_intelligence()
    load_factor = env_intel.get_system_load_factor()
    
    overall_status = "healthy"
    if unhealthy_count > 0:
        overall_status = "degraded"
    if unhealthy_count > len(services) / 2:
        overall_status = "unhealthy"
    
    return {
        "overall_status": overall_status,
        "total_services": len(services),
        "healthy_services": healthy_count,
        "unhealthy_services": unhealthy_count,
        "system_load": round(load_factor, 2),
        "health_checks": health_checks,
        "timestamp": "current"
    }

if __name__ == "__main__":
    svc.run(dev=True)