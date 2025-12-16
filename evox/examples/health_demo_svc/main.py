"""
Health Demo Service - Self-introspection example

This service demonstrates:
- Exposing /capabilities, /health endpoints
- Optional management endpoints
- Observer-only management pattern
"""

from evox import ServiceBuilder, Intent
import psutil
import time

# Create service
service = ServiceBuilder("health-demo-service")

# Service capabilities endpoint
@service.endpoint("/capabilities", methods=["GET"])
@Intent(cacheable=True, ttl=60)
async def get_capabilities():
    """Get service capabilities and features"""
    return {
        "service": "health-demo-service",
        "version": "1.0.0",
        "features": [
            "self-introspection",
            "health-monitoring",
            "capability-discovery",
            "observer-pattern"
        ],
        "supported_intents": [
            "cacheable",
            "strong_consistency",
            "eventual_consistency"
        ],
        "supported_methods": [
            "GET", "POST", "PUT", "DELETE"
        ],
        "data_formats": [
            "JSON"
        ]
    }

# Basic health endpoint (automatically provided by ServiceBuilder)
# Custom health endpoint with more details
@service.endpoint("/health", methods=["GET"])
@Intent(cacheable=True, ttl=30)
async def get_detailed_health():
    """Get detailed health information"""
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    return {
        "status": "healthy",
        "service": "health-demo-service",
        "timestamp": time.time(),
        "system": {
            "cpu_usage": f"{cpu_percent}%",
            "memory_usage": f"{memory.percent}%",
            "memory_available": f"{memory.available / (1024*1024):.2f} MB"
        },
        "uptime": "Service running normally"
    }

# Readiness probe endpoint
@service.endpoint("/ready", methods=["GET"])
@Intent(cacheable=True, ttl=10)
async def readiness_probe():
    """Check if service is ready to accept traffic"""
    # In a real implementation, this would check dependencies
    return {
        "status": "ready",
        "service": "health-demo-service",
        "checks": {
            "database": "connected",
            "cache": "available",
            "dependencies": "ok"
        }
    }

# Liveness probe endpoint
@service.endpoint("/alive", methods=["GET"])
@Intent(cacheable=False)
async def liveness_probe():
    """Check if service is alive"""
    return {
        "status": "alive",
        "service": "health-demo-service",
        "timestamp": time.time()
    }

# Optional management endpoints (observer-only pattern)
@service.endpoint("/management/stats", methods=["GET"])
@Intent(cacheable=True, ttl=60)
async def get_management_stats():
    """Get management statistics (optional, read-only)"""
    return {
        "requests_processed": 1234,
        "errors_count": 5,
        "avg_response_time": "45ms",
        "active_connections": 12
    }

@service.endpoint("/management/config", methods=["GET"])
@Intent(cacheable=True, ttl=300)
async def get_management_config():
    """Get current configuration (read-only)"""
    return {
        "service": "health-demo-service",
        "port": 8004,
        "storage_backend": "memory",
        "cache_enabled": True,
        "cache_ttl": 300
    }

# Metrics endpoint for monitoring
@service.endpoint("/metrics", methods=["GET"])
@Intent(cacheable=False)
async def get_metrics():
    """Get service metrics for monitoring"""
    return {
        "service": "health-demo-service",
        "metrics": {
            "requests_total": 1234,
            "requests_success": 1229,
            "requests_error": 5,
            "latency_avg_ms": 45,
            "latency_p95_ms": 87,
            "latency_p99_ms": 120
        },
        "timestamp": time.time()
    }

# Service discovery endpoint
@service.endpoint("/discovery", methods=["GET"])
@Intent(cacheable=True, ttl=60)
async def service_discovery():
    """Discover available endpoints and services"""
    return {
        "service": "health-demo-service",
        "endpoints": [
            {"path": "/capabilities", "methods": ["GET"], "description": "Service capabilities"},
            {"path": "/health", "methods": ["GET"], "description": "Health status"},
            {"path": "/ready", "methods": ["GET"], "description": "Readiness probe"},
            {"path": "/alive", "methods": ["GET"], "description": "Liveness probe"},
            {"path": "/management/stats", "methods": ["GET"], "description": "Management statistics"},
            {"path": "/management/config", "methods": ["GET"], "description": "Configuration info"},
            {"path": "/metrics", "methods": ["GET"], "description": "Service metrics"},
            {"path": "/discovery", "methods": ["GET"], "description": "Service discovery"}
        ],
        "dependencies": [
            {"name": "internal-cache", "status": "healthy"},
            {"name": "data-storage", "status": "healthy"}
        ]
    }

if __name__ == "__main__":
    service.run()