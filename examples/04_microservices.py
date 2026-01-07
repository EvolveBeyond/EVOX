"""
EVOX Microservices Architecture Demo
====================================

This example demonstrates building a distributed system with EVOX:
- Multiple interconnected services
- Service discovery and registration
- Proxy-based service communication
- Shared data models
- Cross-service messaging
- Distributed caching

Shows how to build scalable microservice architectures with EVOX.
"""

from evoid import (
    service, get, post, put, delete, Body, Param,
    proxy, service_registry, initialize_service_registry,
    message_bus, publish_message, subscribe_to_messages,
    cache_layer, cached,
    data_io, persistence_gateway
)
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import uuid


# === SHARED MODELS ===

class Product(BaseModel):
    """Shared product model used across services"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    category: str
    stock_quantity: int
    created_at: datetime = Field(default_factory=datetime.now)


class OrderItem(BaseModel):
    """Order item model"""
    product_id: str
    quantity: int
    price: float


class Order(BaseModel):
    """Order model"""
    id: str = Field(default_factory=lambda: f"order_{uuid.uuid4().hex[:12]}")
    customer_id: str
    items: List[OrderItem]
    total_amount: float
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)


# === PRODUCT SERVICE ===

product_svc = service("product-service").port(8001).build()

# In-memory product storage
products_db = {}


@product_svc.endpoint("/products", methods=["GET"])
async def list_products(category: Optional[str] = None) -> Dict[str, Any]:
    """List all products, optionally filtered by category"""
    if category:
        filtered = [p for p in products_db.values() if p.category == category]
        return {"products": [p.model_dump() for p in filtered], "count": len(filtered)}
    return {"products": [p.model_dump() for p in products_db.values()], "count": len(products_db)}


@product_svc.endpoint("/products", methods=["POST"])
async def create_product(product: Product = Body(...)) -> Dict[str, Any]:
    """Create a new product"""
    products_db[product.id] = product
    await publish_message("product.created", product.model_dump())
    return {"product": product.model_dump(), "status": "created"}


@product_svc.endpoint("/products/{product_id}", methods=["GET"])
async def get_product(product_id: str = Param(str)) -> Dict[str, Any]:
    """Get product by ID"""
    product = products_db.get(product_id)
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": product.model_dump()}


@product_svc.endpoint("/products/{product_id}/stock", methods=["PUT"])
async def update_stock(
    product_id: str = Param(str),
    new_quantity: int = Body(..., embed=True)
) -> Dict[str, Any]:
    """Update product stock quantity"""
    product = products_db.get(product_id)
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")
    
    old_quantity = product.stock_quantity
    product.stock_quantity = new_quantity
    
    await publish_message("product.stock_updated", {
        "product_id": product_id,
        "old_quantity": old_quantity,
        "new_quantity": new_quantity
    })
    
    return {"product_id": product_id, "old_stock": old_quantity, "new_stock": new_quantity}


# === ORDER SERVICE ===

order_svc = service("order-service").port(8002).build()

# In-memory order storage
orders_db = {}


@order_svc.endpoint("/orders", methods=["POST"])
async def create_order(order_data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Create a new order"""
    # Validate products exist and have sufficient stock
    items = []
    total = 0.0
    
    for item_data in order_data["items"]:
        # Call Product Service via proxy
        try:
            product_response = await proxy.call(
                service="product-service",
                method="GET",
                path=f"/products/{item_data['product_id']}"
            )
            
            product = Product(**product_response["product"])
            if product.stock_quantity < item_data["quantity"]:
                raise ValueError(f"Insufficient stock for {product.name}")
            
            item = OrderItem(
                product_id=item_data["product_id"],
                quantity=item_data["quantity"],
                price=product.price
            )
            items.append(item)
            total += item.price * item.quantity
            
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Product validation failed: {str(e)}")
    
    # Create order
    order = Order(
        customer_id=order_data["customer_id"],
        items=items,
        total_amount=total
    )
    
    orders_db[order.id] = order
    
    # Update product stock
    for item in items:
        product = products_db[item.product_id]
        product.stock_quantity -= item.quantity
        await publish_message("product.stock_updated", {
            "product_id": item.product_id,
            "old_quantity": product.stock_quantity + item.quantity,
            "new_quantity": product.stock_quantity
        })
    
    await publish_message("order.created", order.model_dump())
    
    return {"order": order.model_dump(), "status": "created"}


@cached(ttl_minutes=30)
@order_svc.endpoint("/orders/{order_id}", methods=["GET"])
async def get_order(order_id: str = Param(str)) -> Dict[str, Any]:
    """Get order by ID (cached)"""
    order = orders_db.get(order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order": order.model_dump()}


@order_svc.endpoint("/orders/{order_id}/cancel", methods=["POST"])
async def cancel_order(order_id: str = Param(str)) -> Dict[str, Any]:
    """Cancel an order and restore stock"""
    order = orders_db.get(order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "pending":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    
    # Restore stock
    for item in order.items:
        product = products_db[item.product_id]
        product.stock_quantity += item.quantity
        await publish_message("product.stock_restored", {
            "product_id": item.product_id,
            "quantity": item.quantity
        })
    
    order.status = "cancelled"
    await publish_message("order.cancelled", {"order_id": order_id, "status": "cancelled"})
    
    return {"order_id": order_id, "status": "cancelled"}


# === EVENT HANDLERS ===

@subscribe_to_messages("order.created")
async def handle_order_created(message: Dict[str, Any]):
    """Handle order creation events"""
    print(f"📝 Order {message['id']} created for customer {message['customer_id']}")
    print(f"   Total amount: ${message['total_amount']:.2f}")
    print(f"   Items: {len(message['items'])}")


@subscribe_to_messages("product.stock_updated")
async def handle_stock_update(message: Dict[str, Any]):
    """Handle product stock updates"""
    print(f"📦 Stock updated for product {message['product_id']}: "
          f"{message['old_quantity']} → {message['new_quantity']}")


# === API GATEWAY SERVICE ===

gateway_svc = service("api-gateway").port(8000).build()


@gateway_svc.endpoint("/shop/products", methods=["GET"])
async def gateway_list_products(category: Optional[str] = None) -> Dict[str, Any]:
    """Gateway endpoint for listing products"""
    response = await proxy.call(
        service="product-service",
        method="GET",
        path="/products",
        params={"category": category} if category else {}
    )
    return response


@gateway_svc.endpoint("/shop/orders", methods=["POST"])
async def gateway_create_order(order_data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Gateway endpoint for creating orders"""
    response = await proxy.call(
        service="order-service",
        method="POST",
        path="/orders",
        body=order_data
    )
    return response


# === SERVICE REGISTRY SETUP ===

async def setup_services():
    """Initialize service registry and register all services"""
    await initialize_service_registry()
    
    # Register services
    service_registry.register_service("product-service", "http://localhost:8001")
    service_registry.register_service("order-service", "http://localhost:8002")
    service_registry.register_service("api-gateway", "http://localhost:8000")


# === DEMO DATA ===

async def seed_demo_data():
    """Add some sample products for testing"""
    demo_products = [
        Product(name="Laptop", price=999.99, category="electronics", stock_quantity=50),
        Product(name="Mouse", price=29.99, category="electronics", stock_quantity=200),
        Product(name="Coffee Mug", price=12.99, category="home", stock_quantity=100),
        Product(name="Desk Lamp", price=45.99, category="home", stock_quantity=30)
    ]
    
    for product in demo_products:
        products_db[product.id] = product
        await publish_message("product.created", product.model_dump())


if __name__ == "__main__":
    print("🏪 EVOX Microservices Architecture Demo")
    print("=" * 42)
    print()
    print("Services Included:")
    print("📦 Product Service (port 8001)")
    print("   • Manage product catalog")
    print("   • Handle inventory/stock")
    print()
    print("📋 Order Service (port 8002)")
    print("   • Process customer orders")
    print("   • Validate product availability")
    print("   • Manage order lifecycle")
    print()
    print("🚪 API Gateway (port 8000)")
    print("   • Unified entry point")
    print("   • Route to backend services")
    print()
    print("Architecture Features:")
    print("✅ Service-to-service communication via proxy")
    print("✅ Event-driven architecture with message bus")
    print("✅ Service discovery and registry")
    print("✅ Cross-service data consistency")
    print("✅ Cached responses for performance")
    print()
    print("To run all services:")
    print("1. python 04_microservices.py --service product")
    print("2. python 04_microservices.py --service order") 
    print("3. python 04_microservices.py --service gateway")
    print()
    print("Or run individual service files:")
    print("• product_service.py")
    print("• order_service.py")
    print("• gateway_service.py")