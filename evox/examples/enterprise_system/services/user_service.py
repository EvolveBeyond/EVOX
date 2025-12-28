"""
Enterprise User Service
======================

A professional user management service demonstrating:
- Multi-service architecture
- Service-to-service communication via ServiceRegistry
- BaseProvider pattern implementation
- HealthAwareInject for dependency management
- Multi-layered caching with Redis -> In-Memory fallback
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel
from evox import service, get, post, put, delete, Param, Body
from evox.core.inject import HealthAwareInject
from evox.core.registry import get_service_registry
from evox.core.data_io import data_io
from ..shared.models import User, ServiceCommunicationRequest
from ..providers.base_provider import DataProvider, CommunicationProvider


class UserService:
    """
    Enterprise User Service with Multi-Layered Architecture
    
    This service demonstrates enterprise-grade architecture with:
    - Intent-aware data handling
    - Multi-layered caching system
    - Service-to-service communication
    - Health-aware dependency injection
    - Professional error handling
    """
    
    def __init__(self):
        self._data_provider = DataProvider("user-data-provider", "users")
        self._comm_provider = CommunicationProvider("user-comm-provider")
        self._registry = get_service_registry()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the user service and its providers."""
        if not self._initialized:
            await self._data_provider.initialize()
            await self._comm_provider.initialize()
            self._initialized = True
    
    async def get_user(self, user_id: str) -> User | None:
        """
        Retrieve a user with multi-layered cache fallback.
        
        This method demonstrates the enterprise caching strategy:
        1. Check Redis (if configured)
        2. Fall back to In-Memory cache
        3. Load from persistent storage if needed
        """
        await self.initialize()
        
        # Try to get user from multi-layered cache
        user_data = await self._data_provider.get(f"user:{user_id}")
        
        if user_data:
            return User(**user_data)
        
        # If not in cache, we would load from persistent storage
        # For this example, we'll return None (in a real system, 
        # this would load from a database)
        return None
    
    async def create_user(self, user: User) -> User:
        """
        Create a new user with intent-aware processing.
        
        This method demonstrates enterprise data handling where
        different intents trigger appropriate storage/consistency behaviors.
        """
        await self.initialize()
        
        # Generate ID if not provided
        if not user.id:
            user.id = str(uuid.uuid4())
        
        # Set timestamps
        now = datetime.now().isoformat()
        user.created_at = now
        user.updated_at = now
        
        # Store in multi-layered cache system
        await self._data_provider.set(f"user:{user.id}", user.model_dump(), ttl=3600)
        
        # Notify other services about the new user (service-to-service communication)
        await self._notify_services_user_created(user)
        
        return user
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> User | None:
        """
        Update a user with cache invalidation and service notification.
        
        This method demonstrates enterprise update patterns with proper
        cache management and cross-service communication.
        """
        await self.initialize()
        
        # Get existing user
        existing_user = await self.get_user(user_id)
        if not existing_user:
            return None
        
        # Update the user data
        for key, value in user_data.items():
            if hasattr(existing_user, key):
                setattr(existing_user, key, value)
        
        # Update timestamp
        existing_user.updated_at = datetime.now().isoformat()
        
        # Update in cache
        await self._data_provider.set(
            f"user:{existing_user.id}", 
            existing_user.model_dump(), 
            ttl=3600
        )
        
        # Notify other services about the update
        await self._notify_services_user_updated(existing_user)
        
        return existing_user
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user with cache invalidation and service notification.
        
        This method demonstrates proper cleanup in an enterprise system
        with cache invalidation and cross-service communication.
        """
        await self.initialize()
        
        # Get user before deletion for notification
        user = await self.get_user(user_id)
        if not user:
            return False
        
        # Delete from cache
        await self._data_provider.delete(f"user:{user_id}")
        
        # Notify other services about the deletion
        await self._notify_services_user_deleted(user)
        
        return True
    
    async def _notify_services_user_created(self, user: User):
        """Notify other services about user creation."""
        try:
            # Create communication request
            request = ServiceCommunicationRequest(
                target_service="audit-service",
                operation="log_user_creation",
                payload={"user": user.model_dump(), "action": "created"},
                priority="normal"
            )
            
            # Call the audit service
            await self._comm_provider.call_service(
                "audit-service",
                "log_user_creation",
                user=user.model_dump()
            )
        except Exception as e:
            print(f"Warning: Could not notify services about user creation: {e}")
    
    async def _notify_services_user_updated(self, user: User):
        """Notify other services about user update."""
        try:
            await self._comm_provider.call_service(
                "audit-service",
                "log_user_update",
                user=user.model_dump()
            )
        except Exception as e:
            print(f"Warning: Could not notify services about user update: {e}")
    
    async def _notify_services_user_deleted(self, user: User):
        """Notify other services about user deletion."""
        try:
            await self._comm_provider.call_service(
                "audit-service", 
                "log_user_deletion",
                user=user.model_dump()
            )
        except Exception as e:
            print(f"Warning: Could not notify services about user deletion: {e}")


# Initialize the service instance
user_service = UserService()
HealthAwareInject.register_instance("enterprise_user_service", user_service)


@get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for the user service."""
    # Check the health of our providers
    user_service_health = await user_service._data_provider.health_check()
    comm_health = await user_service._comm_provider.health_check()
    
    overall_status = "healthy" if (
        user_service_health.get("healthy", False) and 
        comm_health.get("healthy", False)
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "user-service",
        "providers": {
            "data_provider": user_service_health.get("status", "unknown"),
            "comm_provider": comm_health.get("status", "unknown")
        }
    }


@get("/users/{user_id}")
async def get_user_endpoint(
    user_id: str = Param(str, description="The user ID to retrieve")
) -> User | Dict[str, str]:
    """Get a specific user by ID."""
    try:
        service = HealthAwareInject["UserService"]()
        user = await service.get_user(user_id)
        
        if user:
            return user
        return {"error": f"User {user_id} not found"}
    except Exception as e:
        return {"error": f"Failed to retrieve user: {str(e)}"}


@post("/users")
async def create_user_endpoint(
    user: User = Body(..., description="User data to create")
) -> User:
    """Create a new user."""
    try:
        service = HealthAwareInject["UserService"]()
        created_user = await service.create_user(user)
        return created_user
    except Exception as e:
        return {"error": f"Failed to create user: {str(e)}"}


@put("/users/{user_id}")
async def update_user_endpoint(
    user_id: str,
    user_data: Dict[str, Any] = Body(..., description="User data to update")
) -> User | Dict[str, str]:
    """Update an existing user."""
    try:
        service = HealthAwareInject["UserService"]()
        updated_user = await service.update_user(user_id, user_data)
        
        if updated_user:
            return updated_user
        return {"error": f"User {user_id} not found"}
    except Exception as e:
        return {"error": f"Failed to update user: {str(e)}"}


@delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: str = Param(str, description="The user ID to delete")
) -> Dict[str, bool]:
    """Delete a user by ID."""
    try:
        service = HealthAwareInject["UserService"]()
        success = await service.delete_user(user_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Register this service with the ServiceRegistry
async def register_service():
    """Register this service with the central registry."""
    registry = get_service_registry()
    await registry.register_service(
        "user-service",
        service_type="user-management",
        metadata={
            "port": 8002,
            "version": "1.0.0",
            "features": ["user-management", "multi-layered-cache", "service-communication"]
        }
    )


# Create and configure the service using EVOX
user_svc = service("user-service") \
    .port(8002) \
    .on_startup(register_service) \
    .build()


async def demonstrate_enterprise_features():
    """
    Demonstrate the enterprise features of this service.
    """
    print("🏢 EVOX Enterprise System - User Service Blue-Print")
    print("=" * 55)
    
    print("\n🎯 Enterprise Architecture Features:")
    print("• Multi-service architecture with clear separation of concerns")
    print("• BaseProvider pattern for consistent provider behavior")
    print("• ServiceRegistry for service discovery and communication")
    print("• HealthAwareInject for resilient dependency management")
    print("• Multi-layered caching with Redis -> In-Memory fallback")
    
    print("\n💡 Professional Design Decisions:")
    print("• Intent-aware data handling")
    print("• Service-to-service communication patterns")
    print("• Proper error handling and fallback mechanisms")
    print("• Audit trail for all operations")
    print("• Health monitoring and status reporting")
    
    print("\n✨ Built with Python 3.13+ Modern Syntax:")
    print("• Union syntax: X | Y instead of Union[X, Y]")
    print("• Enhanced type annotations")
    print("• Modern async/await patterns")
    
    print("\n✅ Enterprise Service ready to run with: user_svc.run(dev=True)")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_enterprise_features())
    
    # Uncomment the following line to run the service
    # user_svc.run(dev=True)