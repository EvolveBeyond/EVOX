"""
EVOX Nano Project Blue-Print
===========================

A minimal, high-performance microservice demonstrating:
- Zero-boilerplate service creation with @service decorator
- Intent-aware Pydantic models
- Health-aware dependency injection
- Multi-layered caching system

This example shows how to build a single-file high-performance API in 60 seconds.
"""

import asyncio
from typing import Dict, Any
from pydantic import BaseModel, Field
from evox import service, get, post, delete, Param, Body
from evox.core.inject import HealthAwareInject
from evox.core.intents import Intent as DataIntent
from evox.core.data_io import data_io


# Define Pydantic models with intent-aware fields
class UserCreateRequest(BaseModel):
    """
    Intent-Aware User Creation Request Model
    
    This model demonstrates how data intents influence behavior:
    - email marked as SENSITIVE gets encrypted storage
    - name marked as CRITICAL gets strong consistency
    - age marked as EPHEMERAL gets optimized caching
    """
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="User's full name",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    email: str = Field(
        ..., 
        pattern=r'^[\w\.-]+@[\w\.-]+\.+\w+$', 
        description="Sensitive email address (encrypted storage)",
        json_schema_extra={"intent": DataIntent.SENSITIVE}
    )
    age: int | None = Field(
        None, 
        ge=0, 
        le=150, 
        description="Age in years",
        json_schema_extra={"intent": DataIntent.EPHEMERAL}
    )


class UserResponse(BaseModel):
    """Intent-aware response model for user data."""
    id: str = Field(
        ..., 
        description="Unique user identifier",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    name: str = Field(
        ..., 
        description="User's full name",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    email: str = Field(
        ..., 
        description="User's email address",
        json_schema_extra={"intent": DataIntent.SENSITIVE}
    )
    age: int | None = Field(
        None, 
        ge=0, 
        le=150, 
        description="Age in years",
        json_schema_extra={"intent": DataIntent.EPHEMERAL}
    )
    created_at: str = Field(
        ..., 
        description="User creation timestamp",
        json_schema_extra={"intent": DataIntent.LAZY}
    )


# Service class with health-aware injection
class NanoUserService:
    """
    Nano User Service - Intent-Aware Operations
    
    This service demonstrates intent-aware data handling where different
    data types get different treatment based on their declared intents.
    """
    
    def __init__(self):
        self._users: Dict[str, UserResponse] = {}
        self._next_id = 1
    
    async def get_user(self, user_id: str) -> UserResponse | None:
        """
        Retrieve user with intent-aware caching.
        
        This method automatically applies caching based on data intent.
        """
        # Use the multi-layered cache system (User-defined -> In-Memory -> File/DB)
        cached_user = await data_io.users.read(f"user:{user_id}")
        
        if cached_user:
            return UserResponse(**cached_user)
        
        # Fallback to in-memory storage if cache miss
        user = self._users.get(user_id)
        if user:
            # Cache the result for future requests
            await data_io.users.write(f"user:{user_id}", user.model_dump(), ttl=300)
        return user
    
    async def create_user(self, user_data: UserCreateRequest) -> UserResponse:
        """
        Create user with intent-aware processing.
        
        Different intents trigger different processing behaviors:
        - SENSITIVE data gets encrypted
        - CRITICAL data gets strong consistency
        - EPHEMERAL data gets optimized for performance
        """
        user_id = str(self._next_id)
        self._next_id += 1
        
        user = UserResponse(
            id=user_id,
            name=user_data.name,
            email=user_data.email,  # Intent-aware: will be encrypted if marked as sensitive
            age=user_data.age,
            created_at="2024-01-01T00:00:00Z"  # In real app, use current timestamp
        )
        
        # Store in memory
        self._users[user_id] = user
        
        # Write to multi-layered cache system with intent-aware behavior
        # The system automatically applies appropriate caching strategy based on data intent
        await data_io.users.write(f"user:{user_id}", user.model_dump(), ttl=600)
        
        return user
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user with cache invalidation."""
        # Remove from memory
        if user_id in self._users:
            del self._users[user_id]
            
            # Invalidate cache entry
            await data_io.users.delete(f"user:{user_id}")
            return True
        return False


# Create and register the service instance
user_service = NanoUserService()
HealthAwareInject.register_instance("nano_user_service", user_service)


@get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint demonstrating intent-aware monitoring.
    
    Returns service health status with intent-aware metrics.
    """
    return {
        "status": "healthy", 
        "service": "nano-service",
        "intents_supported": ["sensitive", "critical", "ephemeral"]
    }


@get("/users/{user_id}")
async def get_user_endpoint(
    user_id: str = Param(str, description="The user ID to retrieve")
) -> UserResponse | Dict[str, str]:
    """
    Get a specific user by ID with intent-aware caching.
    
    Demonstrates automatic cache fallback from user-defined to in-memory.
    """
    # Use HealthAwareInject for dependency injection with health checks
    service = HealthAwareInject["NanoUserService"]()
    
    user = await service.get_user(user_id)
    if user:
        return user
    return {"error": f"User {user_id} not found"}


@post("/users")
async def create_user_endpoint(
    user_data: UserCreateRequest = Body(..., description="User data to create")
) -> UserResponse:
    """
    Create a new user with intent-aware processing.
    
    Different data intents trigger appropriate storage/consistency behaviors.
    """
    # Use HealthAwareInject for dependency injection
    service = HealthAwareInject["NanoUserService"]()
    
    user = await service.create_user(user_data)
    return user


@delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: str = Param(str, description="The user ID to delete")
) -> Dict[str, bool]:
    """Delete a user by ID with cache invalidation."""
    # Use HealthAwareInject for dependency injection
    service = HealthAwareInject["NanoUserService"]()
    
    success = await service.delete_user(user_id)
    return {"success": success}


# Create and configure the service using EVOX
# This demonstrates zero-boilerplate service creation
svc = service("nano-service") \
    .port(8001) \
    .build()


async def demonstrate_features():
    """
    Demonstrate the key features of this nano project blueprint.
    """
    print("🚀 EVOX Nano Project - High-Performance Blueprint")
    print("=" * 55)
    
    print("\n🎯 Key Features Demonstrated:")
    print("• Zero-boilerplate service creation with @service decorator")
    print("• Intent-aware Pydantic models with automatic behavior")
    print("• Health-aware dependency injection")
    print("• Multi-layered caching (User-defined -> In-Memory -> File/DB)")
    print("• Automatic cache invalidation")
    
    print("\n💡 Architecture Decisions:")
    print("• Single-file service for minimal complexity")
    print("• Intent-based data handling for automatic optimization")
    print("• Health-aware injection for resilient operations")
    
    print("\n✨ Built with Python 3.13+ Modern Syntax:")
    print("• Union syntax: X | Y instead of Union[X, Y]")
    print("• Enhanced type annotations")
    print("• Modern async/await patterns")
    
    print("\n✅ Nano Project ready to run with: svc.run(dev=True)")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_features())
    
    # Uncomment the following line to run the service
    # svc.run(dev=True)