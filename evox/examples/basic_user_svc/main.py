"""
Basic User Service - Function-based syntax example

This service demonstrates:
- Function-based syntax (default, minimal)
- Multi-method endpoints
- Data-intent annotations
- Lazy inject.service for inter-service calls
- Param/Body usage
"""

from evox import ServiceBuilder, Param, Body, Intent
from pydantic import BaseModel
from typing import Optional

# Define data models
class UserCreate(BaseModel):
    name: str
    email: str
    age: int

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

# Create service
service = ServiceBuilder("basic-user-service")

# In-memory storage for demo purposes
users_db = {}

# Multi-method endpoint demonstrating different HTTP verbs on the same resource
@service.endpoint("/{user_id}", methods=["GET", "PUT", "DELETE"])
@Intent(cacheable=True)  # This operation can be cached
async def user_operations(user_id: str = Param(), update_data: UserUpdate = Body(None)):
    """
    Handle user operations:
    - GET: Retrieve user by ID
    - PUT: Update user by ID
    - DELETE: Remove user by ID
    """
    if update_data:  # PUT request
        if user_id in users_db:
            # Update existing user
            if update_data.name is not None:
                users_db[user_id]["name"] = update_data.name
            if update_data.email is not None:
                users_db[user_id]["email"] = update_data.email
            if update_data.age is not None:
                users_db[user_id]["age"] = update_data.age
            return {"message": "User updated", "user": users_db[user_id]}
        else:
            return {"error": "User not found"}, 404
    
    # Check if this is a DELETE request
    import inspect
    frame = inspect.currentframe()
    request = frame.f_back.f_locals.get('request')
    if request and request.method == "DELETE":
        if user_id in users_db:
            del users_db[user_id]
            return {"message": "User deleted"}
        else:
            return {"error": "User not found"}, 404
    
    # GET request - retrieve user
    if user_id in users_db:
        return users_db[user_id]
    else:
        return {"error": "User not found"}, 404

# POST endpoint for creating users
@service.endpoint("/", methods=["POST"])
@Intent(consistency="strong")  # This operation requires strong consistency
async def create_user(user_data: UserCreate = Body()):
    """Create a new user"""
    user_id = str(len(users_db) + 1)
    users_db[user_id] = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "age": user_data.age
    }
    return {"message": "User created", "user": users_db[user_id]}, 201

# List all users endpoint
@service.endpoint("/", methods=["GET"])
@Intent(cacheable=True, ttl=300)  # Cacheable with 5-minute TTL
async def list_users():
    """List all users"""
    return {"users": list(users_db.values())}

# Example of inter-service communication using lazy injection
@service.endpoint("/stats", methods=["GET"])
async def get_service_stats():
    """Get service statistics by calling another service"""
    # Lazily inject another service (would be resolved at call time)
    # items_service = inject.service("items-service")
    # stats = await items_service.get_stats()
    return {
        "user_count": len(users_db),
        "service_name": "basic-user-service"
    }

if __name__ == "__main__":
    service.run()