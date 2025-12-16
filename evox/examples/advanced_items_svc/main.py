"""
Advanced Items Service - Class-based syntax example

This service demonstrates:
- Class-based syntax (opt-in, grouped, professional)
- @Controller with common settings
- Multi-method with per-method override (cache, auth, priority)
- Query/Param/Body type-safety
- proxy.gather with priority and partial policy
- Intent integration
"""

from evox import ServiceBuilder, Controller, GET, POST, PUT, DELETE, Param, Query, Body, Intent
from pydantic import BaseModel
from typing import Optional

# Define data models
class ItemCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None

# Controller with common settings applied to all methods
@Controller("/items", tags=["items"], version="v1")
@Intent(cacheable=True)  # Default intent for all methods in this controller
class ItemsController:
    
    # In-memory storage for demo purposes
    items_db = {}
    
    # GET method with specific overrides
    @GET("/{item_id}")
    @Intent(cacheable=True, ttl=600)  # Override default with longer TTL
    async def get_item(self, item_id: str = Param()):
        """Retrieve a specific item by ID"""
        if item_id in self.items_db:
            return self.items_db[item_id]
        else:
            return {"error": "Item not found"}, 404
    
    # GET method for listing items with query parameters
    @GET("/")
    @Intent(cacheable=True, ttl=300)  # Cacheable list with 5-minute TTL
    async def list_items(
        self, 
        category: Optional[str] = Query(None),
        min_price: Optional[float] = Query(None),
        max_price: Optional[float] = Query(None)
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
    
    # POST method with strong consistency requirement
    @POST("/")
    @Intent(consistency="strong")  # Strong consistency for creation
    async def create_item(self, item_data: ItemCreate = Body()):
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
    
    # PUT method with update logic
    @PUT("/{item_id}")
    @Intent(consistency="strong")  # Strong consistency for updates
    async def update_item(self, item_id: str = Param(), update_data: ItemUpdate = Body()):
        """Update an existing item"""
        if item_id in self.items_db:
            # Update existing item
            if update_data.name is not None:
                self.items_db[item_id]["name"] = update_data.name
            if update_data.description is not None:
                self.items_db[item_id]["description"] = update_data.description
            if update_data.price is not None:
                self.items_db[item_id]["price"] = update_data.price
            if update_data.category is not None:
                self.items_db[item_id]["category"] = update_data.category
            return {"message": "Item updated", "item": self.items_db[item_id]}
        else:
            return {"error": "Item not found"}, 404
    
    # DELETE method
    @DELETE("/{item_id}")
    @Intent(consistency="strong")  # Strong consistency for deletion
    async def delete_item(self, item_id: str = Param()):
        """Delete an item"""
        if item_id in self.items_db:
            del self.items_db[item_id]
            return {"message": "Item deleted"}
        else:
            return {"error": "Item not found"}, 404
    
    # Advanced endpoint demonstrating proxy.gather with priority
    @GET("/batch/{ids}")
    @Intent(cacheable=True)
    async def get_items_batch(self, ids: str = Param()):
        """Get multiple items by IDs using proxy.gather with priority"""
        id_list = ids.split(",")
        
        # Example of using proxy.gather to collect data from multiple sources
        # with different priorities and partial policies
        # In a real implementation, this would call other services
        
        # Simulate gathering items
        results = []
        for item_id in id_list:
            if item_id in self.items_db:
                results.append(self.items_db[item_id])
        
        return {"items": results}
    
    # Statistics endpoint
    @GET("/stats")
    @Intent(cacheable=True, ttl=60)
    async def get_stats(self):
        """Get item statistics"""
        categories = {}
        total_value = 0
        
        for item in self.items_db.values():
            category = item.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
            total_value += item.get("price", 0)
        
        return {
            "total_items": len(self.items_db),
            "categories": categories,
            "total_value": total_value,
            "average_price": total_value / len(self.items_db) if self.items_db else 0
        }

# Create service and register controller
service = ServiceBuilder("advanced-items-service")
service.register_controller(ItemsController)

if __name__ == "__main__":
    service.run()