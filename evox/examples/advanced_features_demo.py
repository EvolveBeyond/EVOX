"""
Advanced Features Demo for EVOX
Demonstrates all new features working together with backward compatibility.
"""

from evox import service
from evox.core import get, post, put, delete, Param, Body
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Define API models
from typing import Annotated
from evox.core.data.intents.annotated_intents import Critical, Standard, Ephemeral

class UserCreateRequest(BaseModel):
    name: Annotated[str, Critical(encrypt=False)]  # Critical business data
    email: Annotated[str, Critical(encrypt=True)]  # Critical and sensitive
    age: Annotated[int, Standard()]  # Standard processing

class UserUpdateRequest(BaseModel):
    name: Optional[Annotated[str, Critical(encrypt=False)]] = None
    email: Optional[Annotated[str, Critical(encrypt=True)]] = None
    age: Optional[Annotated[int, Standard()]] = None

class UserResponse(BaseModel):
    id: Annotated[int, Standard()]  # Standard identifier
    name: Annotated[str, Critical(encrypt=False)]
    email: Annotated[str, Critical(encrypt=True)]
    age: Annotated[int, Standard()]
    created_at: Annotated[datetime, Ephemeral()]  # Timestamp can be ephemeral

class UserListResponse(BaseModel):
    users: Annotated[List[UserResponse], Standard()]
    total: Annotated[int, Standard()]

# In-memory storage for demo
users_db = []
next_id = 1

# Create service with advanced features
svc = (
    service("advanced-demo")
    .port(8001)
    .enable_fury_serialization(True)  # Enable high-performance Fury serialization
    .configure_cache(l1_size_mb=50, redis_url="redis://localhost:6379")  # Configure caching
    .enable_benchmarking(True)  # Enable benchmarking endpoints
    .with_message_bus()  # Enable message bus
    .with_task_manager()  # Enable background task management
    .with_model_mapping()  # Enable model mapping
)

# Register model mappings (API model to core model)
# svc.register_model_mapping(UserCreateRequest, UserResponse)
# svc.register_model_mapping(UserUpdateRequest, UserResponse)

@get("/users", intent="user_management", priority="high", serialization="json")
async def get_users():
    """Get all users with high priority"""
    return UserListResponse(
        users=users_db,
        total=len(users_db)
    )

@get("/users/{user_id}", intent="user_management", priority="high", serialization="json")
async def get_user(user_id: int = Param(int)):
    """Get specific user with high priority"""
    for user in users_db:
        if user.id == user_id:
            return user
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="User not found")

@post("/users", intent="user_management", priority="medium", serialization="fury")
async def create_user(request: UserCreateRequest = Body(UserCreateRequest)):
    """Create new user with medium priority and Fury serialization"""
    global next_id
    user = UserResponse(
        id=next_id,
        name=request.name,
        email=request.email,
        age=request.age,
        created_at=datetime.now()
    )
    users_db.append(user)
    next_id += 1
    
    # Publish message about user creation
    from evox.core import publish_message
    await publish_message("user.created", {"user_id": user.id, "name": user.name})
    
    # Schedule background task for analytics
    from evox.core import run_in_background
    run_in_background(analyze_user_creation, user.id)
    
    return user

@put("/users/{user_id}", intent="user_management", priority="medium", serialization="json")
async def update_user(user_id: int, request: UserUpdateRequest = Body(UserUpdateRequest)):
    """Update user with medium priority"""
    for i, user in enumerate(users_db):
        if user.id == user_id:
            updated_data = request.dict(exclude_unset=True)
            for field, value in updated_data.items():
                setattr(users_db[i], field, value)
            return users_db[i]
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="User not found")

@delete("/users/{user_id}", intent="user_management", priority="low", serialization="json")
async def delete_user(user_id: int):
    """Delete user with low priority"""
    global users_db
    users_db = [user for user in users_db if user.id != user_id]
    return {"message": "User deleted successfully"}

# Background task for analytics
async def analyze_user_creation(user_id: int):
    """Background task to analyze user creation"""
    print(f"Analyzing user creation for user ID: {user_id}")
    # Simulate some processing
    import asyncio
    await asyncio.sleep(1)
    print(f"Analysis complete for user ID: {user_id}")

# Demonstrate caching with a special endpoint
from evox.core import cached
from datetime import timedelta

@get("/analytics/summary", intent="analytics", priority="low", serialization="json")
@cached(ttl=timedelta(minutes=5), key_prefix="analytics")
async def get_analytics_summary():
    """Get analytics summary with caching"""
    # Simulate expensive analytics calculation
    total_users = len(users_db)
    avg_age = sum(u.age for u in users_db) / total_users if total_users > 0 else 0
    
    return {
        "total_users": total_users,
        "avg_age": avg_age,
        "timestamp": datetime.now().isoformat()
    }

# Keep backward compatibility with existing syntax
@svc.endpoint("/legacy/endpoint", methods=["GET"], intent="legacy", priority="medium")
async def legacy_endpoint():
    """Legacy endpoint using old syntax for backward compatibility"""
    return {"message": "This is a legacy endpoint", "status": "working"}

if __name__ == "__main__":
    print("Starting Advanced Features Demo Service...")
    print("Features enabled:")
    print("- Fury serialization: High-performance binary serialization")
    print("- Model mapping: Automatic API ↔ Core model conversion")
    print("- Message bus: Internal pub/sub messaging")
    print("- Task manager: Background task scheduling")
    print("- Multi-tier caching: Memory/Redis/disk caching")
    print("- Performance benchmarking: Built-in performance tools")
    print("- Intent-aware routing: Smart request handling")
    print("- Priority queuing: Request prioritization")
    print("- Backward compatibility: Existing code still works")
    print("")
    print("Endpoints available:")
    print("- GET    /users")
    print("- GET    /users/{user_id}")
    print("- POST   /users")
    print("- PUT    /users/{user_id}")
    print("- DELETE /users/{user_id}")
    print("- GET    /analytics/summary (cached)")
    print("- GET    /legacy/endpoint (backward compatible)")
    print("- GET    /benchmark/serialization (if benchmarking enabled)")
    print("")
    print("Starting server on port 8001...")
    svc.run()