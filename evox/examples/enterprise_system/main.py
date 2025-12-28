"""
EVOX Enterprise System Blue-Print
=================================

A multi-service, class-based architecture demonstrating:
- Professional folder layout (services, providers, shared models)
- BaseProvider pattern implementation
- HealthAwareInject[T] for dependency management
- Multi-Layered Cache (Redis -> In-Memory fallback)
- Service-to-Service communication via ServiceRegistry

This example shows how to build a stable system that survives provider failures.
"""

import asyncio
from typing import Dict, Any
from evox import service
from evox.core.registry import get_service_registry
from evox.core.inject import HealthAwareInject
from .providers.base_provider import BaseProvider, DataProvider, CommunicationProvider
from .services.user_service import UserService, user_svc


class EnterpriseSystemManager:
    """
    Enterprise System Manager
    
    This class manages the entire enterprise system, coordinating between
    different services, providers, and the service registry. It demonstrates
    enterprise-level orchestration patterns.
    """
    
    def __init__(self):
        self._services = {}
        self._providers = {}
        self._registry = get_service_registry()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the entire enterprise system."""
        if self._initialized:
            return
        
        print("🚀 Initializing Enterprise System...")
        
        # Initialize user service
        user_service = UserService()
        await user_service.initialize()
        self._services["user_service"] = user_service
        
        # Initialize providers
        data_provider = DataProvider("enterprise-data-provider", "enterprise")
        comm_provider = CommunicationProvider("enterprise-comm-provider")
        
        await data_provider.initialize()
        await comm_provider.initialize()
        
        self._providers["data"] = data_provider
        self._providers["communication"] = comm_provider
        
        # Register with HealthAwareInject
        HealthAwareInject.register_instance("enterprise_system_manager", self)
        HealthAwareInject.register_instance("enterprise_data_provider", data_provider)
        HealthAwareInject.register_instance("enterprise_comm_provider", comm_provider)
        
        # Register services with the registry
        await self._register_services()
        
        self._initialized = True
        print("✅ Enterprise System initialized successfully")
    
    async def _register_services(self):
        """Register all services with the ServiceRegistry."""
        await self._registry.register_service(
            "enterprise-system",
            service_type="orchestration",
            metadata={
                "version": "1.0.0",
                "features": [
                    "multi-service-orchestration",
                    "enterprise-caching",
                    "service-registry-integration",
                    "health-monitoring"
                ]
            }
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check of the enterprise system."""
        health_results = {
            "system": "enterprise-system",
            "timestamp": "2024-01-01T00:00:00Z",  # In real app, use current timestamp
            "overall_status": "healthy",
            "components": {}
        }
        
        # Check provider health
        for name, provider in self._providers.items():
            health = await provider.health_check()
            health_results["components"][name] = health
            if not health.get("healthy", False):
                health_results["overall_status"] = "unhealthy"
        
        # Check service health
        for name, service in self._services.items():
            if hasattr(service, "_data_provider"):
                service_health = await service._data_provider.health_check()
                health_results["components"][f"{name}_data"] = service_health
                if not service_health.get("healthy", False):
                    health_results["overall_status"] = "unhealthy"
        
        return health_results
    
    async def get_component_status(self) -> Dict[str, Any]:
        """Get detailed status of all system components."""
        status = {
            "services": {},
            "providers": {},
            "registry_status": await self._registry.get_status()
        }
        
        # Service status
        for name, service in self._services.items():
            status["services"][name] = {
                "initialized": getattr(service, '_initialized', False),
                "type": type(service).__name__
            }
        
        # Provider status
        for name, provider in self._providers.items():
            status["providers"][name] = {
                "initialized": provider.initialized,
                "healthy": provider.healthy,
                "type": type(provider).__name__
            }
        
        return status


# Create the enterprise system manager
enterprise_manager = EnterpriseSystemManager()


@service("enterprise-system") \
    .port(8002) \
    .build()


async def demonstrate_enterprise_system():
    """
    Demonstrate the enterprise system features.
    """
    print("🏢 EVOX Enterprise System - Multi-Service Architecture")
    print("=" * 55)
    
    # Initialize the system
    await enterprise_manager.initialize()
    
    print("\n🎯 Enterprise System Features:")
    print("• Multi-service architecture with clear separation of concerns")
    print("• BaseProvider pattern for consistent provider behavior")
    print("• ServiceRegistry for service discovery and communication")
    print("• HealthAwareInject for resilient dependency management")
    print("• Multi-layered caching with automatic fallback")
    
    print("\n💡 Architecture Decisions:")
    print("• Professional folder structure (services, providers, shared)")
    print("• BaseProvider pattern for consistent provider interfaces")
    print("• Service-to-service communication via ServiceRegistry")
    print("• Health-aware operations with fallback mechanisms")
    print("• Centralized system management with EnterpriseSystemManager")
    
    print("\n📋 System Components:")
    status = await enterprise_manager.get_component_status()
    print(f"  Services: {len(status['services'])}")
    print(f"  Providers: {len(status['providers'])}")
    print(f"  Registry Status: {status['registry_status']}")
    
    print("\n🏥 Health Check:")
    health = await enterprise_manager.health_check()
    print(f"  Overall Status: {health['overall_status']}")
    for component, details in health['components'].items():
        status = details.get('healthy', 'unknown')
        print(f"    {component}: {'✅' if status else '❌'}")
    
    print("\n✨ Built with Python 3.13+ Modern Syntax:")
    print("• Union syntax: X | Y instead of Union[X, Y]")
    print("• Enhanced type annotations")
    print("• Modern async/await patterns")
    
    print("\n✅ Enterprise System ready to run individual services")
    print("   Run user service with: user_svc.run(dev=True)")


async def run_enterprise_system():
    """
    Run the enterprise system (this would coordinate multiple services in a real system).
    """
    await enterprise_manager.initialize()
    
    # In a real enterprise system, this would start multiple services
    # For this example, we'll just demonstrate the architecture
    await demonstrate_enterprise_system()


if __name__ == "__main__":
    # Run the enterprise system demonstration
    asyncio.run(run_enterprise_system())