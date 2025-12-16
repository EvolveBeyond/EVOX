"""
Storage Demo Service - Data-intent-aware storage example

This service demonstrates:
- Different intents (cacheable, strong consistency, eventual)
- Unified storage API
- No ORM — pure data_io
- Aggressive cache fallback
"""

from evox import ServiceBuilder, data_io, Intent
from pydantic import BaseModel
import time

# Define data models
class Product(BaseModel):
    id: str
    name: str
    price: float
    description: str
    category: str

# Create service
service = ServiceBuilder("storage-demo-service")

# Demonstrate different data intents
@service.endpoint("/products/{product_id}", methods=["GET"])
@Intent(cacheable=True, ttl=600)  # Cacheable with 10-minute TTL
async def get_product_cached(product_id: str):
    """Retrieve product with cacheable intent"""
    # This operation will be cached based on the intent
    product = await data_io.read(f"product:{product_id}")
    if product:
        return product
    else:
        return {"error": "Product not found"}, 404

@service.endpoint("/products/{product_id}", methods=["POST"])
@Intent(consistency="strong")  # Strong consistency required
async def create_product_strong(product_id: str, product_data: dict):
    """Create product with strong consistency intent"""
    # This operation requires strong consistency - no caching
    await data_io.write(f"product:{product_id}", product_data)
    return {"message": "Product created with strong consistency", "product": product_data}

@service.endpoint("/analytics/{metric_id}", methods=["GET"])
@Intent(consistency="eventual")  # Eventual consistency acceptable
async def get_analytics_eventual(metric_id: str):
    """Retrieve analytics with eventual consistency intent"""
    # This operation can tolerate eventual consistency
    metric = await data_io.read(f"analytics:{metric_id}")
    if metric:
        return metric
    else:
        return {"error": "Metric not found"}, 404

@service.endpoint("/products/bulk", methods=["POST"])
@Intent(consistency="strong")  # Strong consistency for bulk operations
async def bulk_create_products(products: list):
    """Bulk create products with strong consistency"""
    results = []
    for product_data in products:
        product_id = product_data.get("id")
        if product_id:
            await data_io.write(f"product:{product_id}", product_data)
            results.append({"id": product_id, "status": "created"})
        else:
            results.append({"status": "error", "message": "Missing product ID"})
    return {"message": "Bulk operation completed", "results": results}

# Demonstrate aggressive cache fallback
@service.endpoint("/fallback/demo", methods=["GET"])
@Intent(cacheable=True, ttl=300)
async def fallback_demo():
    """Demonstrate aggressive cache fallback"""
    # Try to get fresh data
    try:
        # Simulate a backend that might fail
        if time.time() % 5 < 1:  # Simulate intermittent failure
            raise Exception("Backend temporarily unavailable")
        
        fresh_data = {"timestamp": time.time(), "data": "Fresh data from backend"}
        await data_io.write("fallback_demo", fresh_data, ttl=300)
        return fresh_data
    except Exception as e:
        # Fall back to cached/stale data if available
        cached_data = await data_io.read("fallback_demo")
        if cached_data:
            return {
                "data": cached_data,
                "warning": "Serving cached data due to backend issues",
                "error": str(e)
            }
        else:
            return {"error": "No data available", "details": str(e)}, 503

# Demonstrate unified storage API
@service.endpoint("/storage/unified", methods=["POST"])
async def unified_storage_demo():
    """Demonstrate unified storage API with different intents"""
    # Store data with different intents using the same API
    timestamp = time.time()
    
    # Cacheable data
    cacheable_data = {"type": "cacheable", "timestamp": timestamp, "value": "This can be cached"}
    await data_io.write("unified:cacheable", cacheable_data, ttl=600)
    
    # Strong consistency data
    strong_data = {"type": "strong", "timestamp": timestamp, "value": "This requires strong consistency"}
    await data_io.write("unified:strong", strong_data)
    
    # Eventual consistency data
    eventual_data = {"type": "eventual", "timestamp": timestamp, "value": "This can be eventually consistent"}
    await data_io.write("unified:eventual", eventual_data, ttl=300)
    
    return {
        "message": "Data stored with different intents using unified API",
        "keys": ["unified:cacheable", "unified:strong", "unified:eventual"]
    }

@service.endpoint("/storage/unified/{intent_type}", methods=["GET"])
async def read_unified_storage(intent_type: str):
    """Read data stored with different intents"""
    key = f"unified:{intent_type}"
    data = await data_io.read(key)
    if data:
        return data
    else:
        return {"error": f"No data found for intent type: {intent_type}"}, 404

# Performance comparison endpoint
@service.endpoint("/storage/performance", methods=["GET"])
async def storage_performance_comparison():
    """Compare performance of different storage intents"""
    results = {}
    
    # Test cacheable storage
    start_time = time.time()
    for i in range(100):
        await data_io.write(f"perf:cacheable:{i}", {"value": i}, ttl=300)
    cacheable_write_time = time.time() - start_time
    
    start_time = time.time()
    for i in range(100):
        await data_io.read(f"perf:cacheable:{i}")
    cacheable_read_time = time.time() - start_time
    
    # Test strong consistency storage
    start_time = time.time()
    for i in range(100):
        await data_io.write(f"perf:strong:{i}", {"value": i})
    strong_write_time = time.time() - start_time
    
    start_time = time.time()
    for i in range(100):
        await data_io.read(f"perf:strong:{i}")
    strong_read_time = time.time() - start_time
    
    results = {
        "cacheable": {
            "write_time": cacheable_write_time,
            "read_time": cacheable_read_time,
            "ops_per_second": {
                "write": 100 / cacheable_write_time if cacheable_write_time > 0 else 0,
                "read": 100 / cacheable_read_time if cacheable_read_time > 0 else 0
            }
        },
        "strong": {
            "write_time": strong_write_time,
            "read_time": strong_read_time,
            "ops_per_second": {
                "write": 100 / strong_write_time if strong_write_time > 0 else 0,
                "read": 100 / strong_read_time if strong_read_time > 0 else 0
            }
        }
    }
    
    return {"performance_comparison": results}

if __name__ == "__main__":
    service.run()