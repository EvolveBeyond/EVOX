"""Template Example - Evox Framework Enhanced Features
This template demonstrates the key features of the enhanced Evox framework:
1. Dual syntax support (function-based and class-based)
2. Type-safe lazy dependency injection
3. Intelligent context-aware priority management
4. Environmental intelligence
"""

from evox import service, Controller, GET, POST, PUT, DELETE, Param, Query, Body, Intent
from evox.core.inject import inject
from pydantic import BaseModel
from typing import Optional


# ================================
# DATA MODELS
# ================================

class CreateRequest(BaseModel):
    """Example request model with priority metadata"""
    name: str
    description: str
    priority: Optional[str] = "medium"  # Schema-based priority boost


class UpdateRequest(BaseModel):
    """Example update model"""
    name: Optional[str] = None
    description: Optional[str] = None


# ================================
# FUNCTION-BASED SYNTAX (Default)
# ================================

# Create service with fluent API
service = service("template-service") \
    .port(8000) \
    .health("/health") \
    .build()


# GET endpoint with caching intent
@service.endpoint("/items/{item_id}", methods=["GET"])
@Intent(cacheable=True, ttl=300)
async def get_item(item_id: str = Param(str)):
    """Retrieve item by ID with automatic caching"""
    # Type-safe dependency injection
    db = inject('db')
    config = inject('config')
    
    # Implementation here
    return {"item_id": item_id, "data": "item_data"}


# POST endpoint with strong consistency
@service.endpoint("/items", methods=["POST"])
@Intent(consistency="strong")
async def create_item(item_data: CreateRequest = Body(CreateRequest)):
    """Create new item with strong consistency"""
    # Implementation here
    return {"message": "Item created", "item": item_data.dict()}, 201


# PUT endpoint for updates
@service.endpoint("/items/{item_id}", methods=["PUT"])
@Intent(consistency="strong")
async def update_item(item_id: str = Param(str), update_data: UpdateRequest = Body(UpdateRequest)):
    """Update existing item"""
    # Implementation here
    return {"message": "Item updated"}


# DELETE endpoint
@service.endpoint("/items/{item_id}", methods=["DELETE"])
@Intent(consistency="strong")
async def delete_item(item_id: str = Param(str)):
    """Delete item"""
    # Implementation here
    return {"message": "Item deleted"}


# ================================
# CLASS-BASED SYNTAX (Opt-in)
# ================================

@Controller("/api/v1/resources", tags=["resources"], version="v1")
@Intent(cacheable=True)  # Default intent for all methods
class ResourceController:
    """Class-based controller with shared configuration"""
    
    def __init__(self):
        # Initialize resources
        self.resources = {}
    
    @GET("/{resource_id}")
    @Intent(cacheable=True, ttl=600)
    async def get_resource(self, resource_id: str = Param(str)):
        """Get resource by ID"""
        if resource_id in self.resources:
            return self.resources[resource_id]
        return {"error": "Resource not found"}, 404
    
    @GET("/")
    @Intent(cacheable=True, ttl=120)
    async def list_resources(
        self,
        category: Optional[str] = Query(None),
        limit: Optional[int] = Query(int, 10)
    ):
        """List resources with filtering"""
        # Implementation here
        return {"resources": [], "count": 0}
    
    @POST("/")
    @Intent(consistency="strong")
    async def create_resource(self, resource_data: CreateRequest = Body(CreateRequest)):
        """Create new resource"""
        # Implementation here
        return {"message": "Resource created"}, 201
    
    @PUT("/{resource_id}")
    @Intent(consistency="strong")
    async def update_resource(self, resource_id: str = Param(str), data: UpdateRequest = Body(UpdateRequest)):
        """Update resource"""
        # Implementation here
        return {"message": "Resource updated"}
    
    @DELETE("/{resource_id}")
    @Intent(consistency="strong")
    async def delete_resource(self, resource_id: str = Param(str)):
        """Delete resource"""
        # Implementation here
        return {"message": "Resource deleted"}


# Controllers are automatically registered when service is built
# service.register_controller(ResourceController)


# ================================
# ADVANCED FEATURES DEMONSTRATION
# ================================

@Controller("/advanced", tags=["advanced"], version="v1")
class AdvancedFeaturesController:
    """Demonstrates advanced framework features"""
    
    def __init__(self):
        # Type-safe dependency injection
        self.db = inject('db')
        self.config = inject('config')
        self.other_service = inject.service("other-service")
    
    @POST("/priority-demo")
    async def priority_demo(self, request: CreateRequest):
        """
        Demonstrates intelligent priority management:
        - Schema-based priority boost (from request.priority)
        - Context-aware priority (from headers)
        - Resource-aware concurrency adjustment
        """
        # Implementation here
        return {"message": "Processed with intelligent priority management"}
    
    @GET("/intelligence-demo")
    @Intent(cacheable=True)
    async def intelligence_demo(self):
        """
        Demonstrates environmental intelligence:
        - Automatic caching based on @Intent
        - Context adaptation based on requester
        - Priority determination based on importance
        """
        # Implementation here
        return {
            "message": "Environmental intelligence in action",
            "features": [
                "Automatic caching",
                "Context adaptation",
                "Smart prioritization"
            ]
        }


# Controllers are automatically registered when service is built
# service.register_controller(AdvancedFeaturesController)


# ================================
# SERVICE LIFECYCLE HOOKS
# ================================

@service.on_startup
async def startup():
    """Service startup hook"""
    print("🚀 Template service starting up...")
    # Initialize resources, connections, etc.


@service.on_shutdown
async def shutdown():
    """Service shutdown hook"""
    print("🛑 Template service shutting down...")
    # Clean up resources, connections, etc.


# ================================
# BACKGROUND TASKS
# ================================

@service.background_task(interval=60)
async def periodic_cleanup():
    """Periodic background task"""
    print("🧹 Running periodic cleanup...")
    # Implementation here


# ================================
# MAIN ENTRY POINT
# ================================

if __name__ == "__main__":
    # Run the service
    service.run(dev=True)