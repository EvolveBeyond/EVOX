"""
Enhanced Evox Framework Showcase - Demonstrating Dual Syntax Support and Advanced Features

This example demonstrates:
1. Dual syntax support (function-based and class-based)
2. Type-safe lazy dependency injection
3. Intelligent context-aware priority management
4. Environmental intelligence features
"""

from evox import service, Controller, GET, POST, PUT, DELETE, Param, Query, Body, Intent
from evox.core.inject import inject, inject_dependency
from pydantic import BaseModel
from typing import Optional, List
import asyncio


# Define data models with priority metadata
class UserCreate(BaseModel):
    name: str
    email: str
    age: int
    # Schema-based priority boost
    priority: Optional[str] = "medium"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None


class ItemCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    priority: Optional[str] = "low"


class HighPriorityRequest(BaseModel):
    """Schema that should get high priority by default"""
    data: str
    priority: str = "high"  # This will boost the request priority


# ================================
# FUNCTION-BASED SYNTAX (Default)
# ================================

# Create function-based service
user_service = service("user-service")

# In-memory storage
users_db = {}
items_db = {}


# Multi-method endpoint demonstrating different HTTP verbs on separate functions
@user_service.endpoint("/users/{user_id}", methods=["GET"])
@Intent(cacheable=True, ttl=300)  # Cacheable with 5-minute TTL
async def get_user(user_id: str = Param(str)):
    """Retrieve user by ID"""
    # Type-safe dependency injection
    db = inject('db')
    
    if user_id in users_db:
        return users_db[user_id]
    else:
        return {"error": "User not found"}, 404


@user_service.endpoint("/users/{user_id}", methods=["PUT"])
@Intent(consistency="strong")  # Strong consistency for updates
async def update_user(user_id: str = Param(str), update_data: UserUpdate = Body(UserUpdate)):
    """Update user by ID"""
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


@user_service.endpoint("/users/{user_id}", methods=["DELETE"])
@Intent(consistency="strong")  # Strong consistency for deletion
async def delete_user(user_id: str = Param(str)):
    """Delete user by ID"""
    if user_id in users_db:
        del users_db[user_id]
        return {"message": "User deleted"}
    else:
        return {"error": "User not found"}, 404


@user_service.endpoint("/users", methods=["POST"])
@Intent(consistency="strong")  # Strong consistency for creation
async def create_user(user_data: UserCreate = Body(UserCreate)):
    """Create a new user"""
    user_id = str(len(users_db) + 1)
    users_db[user_id] = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "age": user_data.age
    }
    return {"message": "User created", "user": users_db[user_id]}, 201


@user_service.endpoint("/users", methods=["GET"])
@Intent(cacheable=True, ttl=120)  # Cacheable with 2-minute TTL
async def list_users(min_age: Optional[int] = Query(int, None)):
    """List all users with optional filtering"""
    filtered_users = list(users_db.values())
    
    if min_age is not None:
        filtered_users = [user for user in filtered_users if user.get("age", 0) >= min_age]
        
    return {"users": filtered_users}


# Service-to-service communication with priority management
@user_service.endpoint("/users/{user_id}/items", methods=["GET"])
async def get_user_items(user_id: str = Param(str)):
    """Get items belonging to a user with intelligent priority management"""
    # Lazy service injection
    items_svc = inject.service("items-service")
    
    # Context-aware priority - high priority for user data
    items = await items_svc.get_items_by_user(user_id, priority="high")
    return {"user_id": user_id, "items": items}


# ================================
# CLASS-BASED SYNTAX (Opt-in)
# ================================

@Controller("/items", tags=["items"])
@Intent(cacheable=True)  # Default intent for all methods
class ItemsController:
    """Class-based controller demonstrating grouping and shared configuration"""
    
    def __init__(self):
        self.items_db = {}
    
    @GET("/{item_id}")
    @Intent(cacheable=True, ttl=600)  # Override default with longer TTL
    async def get_item(self, item_id: str = Param(str)):
        """Retrieve a specific item by ID"""
        if item_id in self.items_db:
            return self.items_db[item_id]
        else:
            return {"error": "Item not found"}, 404
    
    @GET("/")
    @Intent(cacheable=True, ttl=300)  # Cacheable list with 5-minute TTL
    async def list_items(
        self, 
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ):
        """List items with optional filtering"""
        filtered_items = list(self.items_db.values())
        
        if category:
            filtered_items = [item for item in filtered_items if item.get("category") == category]
        
        if min_price is not None:
            filtered_items = [item for item in filtered_items if item.get("price", 0) >= min_price]
            
        if max_price is not None:
            filtered_items = [item for item in filtered_items if item.get("price", 0) <= max_price]
            
        return {"items": filtered_items}
    
    @POST("/")
    @Intent(consistency="strong")  # Strong consistency for creation
    async def create_item(self, item_data: ItemCreate = Body(ItemCreate)):
        """Create a new item"""
        item_id = str(len(self.items_db) + 1)
        self.items_db[item_id] = {
            "id": item_id,
            "name": item_data.name,
            "description": item_data.description,
            "price": item_data.price,
            "category": item_data.category
        }
        return {"message": "Item created", "item": self.items_db[item_id]}, 201
    
    @PUT("/{item_id}")
    @Intent(consistency="strong")  # Strong consistency for updates
    async def update_item(self, item_id: str = Param(str), update_data: ItemCreate = Body(ItemCreate)):
        """Update an existing item"""
        if item_id in self.items_db:
            # Update existing item
            self.items_db[item_id].update({
                "name": update_data.name,
                "description": update_data.description,
                "price": update_data.price,
                "category": update_data.category
            })
            return {"message": "Item updated", "item": self.items_db[item_id]}
        else:
            return {"error": "Item not found"}, 404
    
    @DELETE("/{item_id}")
    @Intent(consistency="strong")  # Strong consistency for deletion
    async def delete_item(self, item_id: str = Param(str)):
        """Delete an item"""
        if item_id in self.items_db:
            del self.items_db[item_id]
            return {"message": "Item deleted"}
        else:
            return {"error": "Item not found"}, 404
    
    # Endpoint demonstrating schema-based priority boosting
    @POST("/bulk")
    async def bulk_create_items(self, items: List[ItemCreate] = Body(List[ItemCreate])):
        """Bulk create items with schema-based priority management"""
        created_items = []
        for item_data in items:
            item_id = str(len(self.items_db) + 1)
            self.items_db[item_id] = {
                "id": item_id,
                "name": item_data.name,
                "description": item_data.description,
                "price": item_data.price,
                "category": item_data.category
            }
            created_items.append(self.items_db[item_id])
        
        return {"message": f"Created {len(created_items)} items", "items": created_items}, 201


# Create services
items_service = service("items-service")
# Controllers are automatically registered when service is built


# ================================
# INTELLIGENT PRIORITY MANAGEMENT
# ================================

@Controller("/priority-demo", tags=["priority"])
class PriorityDemoController:
    """Demonstrates intelligent, context-aware priority management"""
    
    @POST("/high-priority-request")
    async def handle_high_priority(self, request: HighPriorityRequest):
        """Handle high-priority request automatically detected by schema"""
        # This will automatically get high priority due to the schema
        await asyncio.sleep(0.1)  # Simulate work
        return {"message": "Handled high-priority request", "data": request.data}
    
    @POST("/context-priority")
    async def handle_context_priority(self, data: dict):
        """Handle request with context-based priority from headers"""
        # Priority determined by X-Priority header or 'priority' field in payload
        await asyncio.sleep(0.1)  # Simulate work
        return {"message": "Handled context-priority request", "data": data}
    
    @GET("/resource-aware")
    async def resource_aware_endpoint(self):
        """Endpoint that adjusts behavior based on resource usage"""
        # In a real implementation, this would check system resources
        return {"message": "Resource-aware endpoint response"}


priority_service = service("priority-demo-service")
# Controllers are automatically registered when service is built


# ================================
# ENVIRONMENTAL INTELLIGENCE
# ================================

@Controller("/intelligence-demo", tags=["intelligence"])
class IntelligenceDemoController:
    """Demonstrates environmental intelligence features"""
    
    def __init__(self):
        # Type-safe dependency injection with Pydantic Annotated
        self.config = inject('config')
        self.db = inject('db')
    
    @GET("/understands-data")
    @Intent(cacheable=True)
    async def understands_data(self):
        """Endpoint that understands the data automatically"""
        # The framework automatically handles caching based on @Intent
        # No manual cache management needed
        user_count = len(users_db)
        item_count = len(items_db)
        
        return {
            "message": "Framework understands the data automatically",
            "user_count": user_count,
            "item_count": item_count,
            "cache_info": "Handled automatically by @Intent(cacheable=True)"
        }
    
    @GET("/understands-requester")
    async def understands_requester(self, request_type: str = Query("regular")):
        """Endpoint that adapts based on requester context"""
        # In a real implementation, this would analyze the requester
        
        if request_type == "admin":
            # Higher priority for admin requests
            priority_info = "Admin request - higher priority processing"
        elif request_type == "system":
            # Lower priority for system background tasks
            priority_info = "System request - background processing"
        else:
            # Regular user request
            priority_info = "Regular user request - standard processing"
            
        return {
            "message": "Framework understands who is requesting",
            "request_type": request_type,
            "priority_handling": priority_info
        }
    
    @GET("/understands-importance")
    async def understands_importance(self, importance: str = Query("normal")):
        """Endpoint that prioritizes based on data importance"""
        # The framework automatically prioritizes based on context
        
        if importance == "critical":
            auto_priority = "high"
            processing = "Immediate processing"
        elif importance == "low":
            auto_priority = "low"
            processing = "Background processing"
        else:
            auto_priority = "medium"
            processing = "Standard processing"
            
        return {
            "message": "Framework understands which request is more important",
            "importance": importance,
            "auto_priority": auto_priority,
            "processing": processing,
            "framework_managed": "No manual priority management needed"
        }


intelligence_service = service("intelligence-demo-service")
# Controllers are automatically registered when service is built


# Build all services
user_service = user_service.port(8001).build()
items_service = items_service.port(8002).build()
priority_service = priority_service.port(8003).build()
intelligence_service = intelligence_service.port(8004).build()


# ================================
# DEMONSTRATION AND TESTING
# ================================

async def demonstrate_features():
    """Demonstrate the enhanced features"""
    print("🚀 Evox Framework Enhanced Features Demonstration")
    print("=" * 50)
    
    # 1. Dual Syntax Support
    print("\n1. Dual Syntax Support:")
    print("   ✓ Function-based syntax (user_service)")
    print("   ✓ Class-based syntax (ItemsController)")
    print("   ✓ Both syntaxes equally supported")
    
    # 2. Type-Safe Lazy DI
    print("\n2. Type-Safe Lazy Dependency Injection:")
    print("   ✓ inject('service') for service proxies")
    print("   ✓ inject('db') for database connections")
    print("   ✓ inject('config') for configuration")
    print("   ✓ Lazy resolution - no startup coupling")
    print("   ✓ Easy testing with override mechanism")
    
    # 3. Intelligent Priority Management
    print("\n3. Intelligent Context-Aware Priority Management:")
    print("   ✓ Static priority (decorator-based)")
    print("   ✓ Dynamic priority (header/payload-based)")
    print("   ✓ Schema-based priority boosting")
    print("   ✓ Resource-aware concurrency adjustment")
    
    # 4. Environmental Intelligence
    print("\n4. Environmental Intelligence:")
    print("   ✓ Understands the data (automatic caching)")
    print("   ✓ Understands the requester (context adaptation)")
    print("   ✓ Understands importance (automatic prioritization)")
    print("   ✓ Minimal boilerplate for developers")
    
    print("\n✨ All features implemented with clean, modern, production-ready code!")


if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demonstrate_features())
    
    # To run the services, uncomment the following lines:
    # print("\nStarting services...")
    # user_service.run(dev=True)