"""
MiniApp Service - Self-introspective dashboard for Evox service

This service provides observer-only introspection capabilities:
- Health monitoring
- Configuration inspection
- Performance metrics
- Service capabilities

Important: This is an OPTIONAL observer service. All operations are READ-ONLY.
Services operate autonomously without dependency on this dashboard.
"""
import tomli
import time
from evox.core import service, get, post, data_io
from evox.core.storage import data_io as storage_data_io
from evox.core.queue import get_priority_queue

# Load configuration
try:
    with open("config.toml", "rb") as f:
        config = tomli.load(f)
except FileNotFoundError:
    config = {}

# Service metadata
SERVICE_METADATA = {
    "name": "miniapp_svc",
    "version": "0.1.0",
    "description": "Self-introspective dashboard service",
    "type": "observer-only"
}

# Create service
svc = service("miniapp_svc") \
    .port(config.get("port", 8002)) \
    .health("/health") \
    .build()

# Service information endpoint
@get("/")
async def service_info():
    """Get service information and capabilities"""
    return {
        "service": SERVICE_METADATA,
        "endpoints": [
            "/health",
            "/config",
            "/metrics",
            "/capabilities"
        ],
        "status": "running",
        "timestamp": time.time()
    }

# Enhanced health endpoint
@get("/health")
async def health():
    """Get enhanced health information"""
    # Get queue stats if available
    queue_stats = {}
    try:
        queue = get_priority_queue()
        queue_stats = queue.get_stats()
    except:
        pass
    
    return {
        "status": "healthy", 
        "service": "miniapp_svc",
        "timestamp": time.time(),
        "queue_stats": queue_stats
    }

# Configuration inspection (READ-ONLY)
@get("/config")
async def inspect_config():
    """Inspect current service configuration (READ-ONLY)"""
    return {
        "config": config,
        "metadata": SERVICE_METADATA,
        "timestamp": time.time()
    }

# Performance metrics
@get("/metrics")
async def metrics():
    """Get service performance metrics"""
    # Get cache stats from data_io
    cache_stats = {}
    try:
        cache_stats = storage_data_io.get_cache_stats()
    except:
        pass
    
    # Get queue stats
    queue_stats = {}
    try:
        queue = get_priority_queue()
        queue_stats = queue.get_stats()
    except:
        pass
    
    return {
        "cache": cache_stats,
        "queue": queue_stats,
        "timestamp": time.time()
    }

# Service capabilities
@get("/capabilities")
async def capabilities():
    """Get service capabilities and supported features"""
    return {
        "service": SERVICE_METADATA,
        "capabilities": [
            "self-introspection",
            "health-monitoring",
            "configuration-inspection",
            "performance-metrics"
        ],
        "constraints": [
            "read-only-access",
            "observer-pattern",
            "no-control-operations"
        ],
        "timestamp": time.time()
    }

if __name__ == "__main__":
    svc.run(dev=True)