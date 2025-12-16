"""
Management Service - Observer-only management plane for Evox platform

This service provides optional centralized monitoring and coordination:
- Service discovery scanning
- Topology visualization
- Health status aggregation
- Optional management operations (pause, scale hints)

Important: This is an OPTIONAL observer-coordinator service.
All Evox services operate autonomously without dependency on this service.
"""

import tomli
import time
import asyncio
from typing import Dict, List, Any
from evox.core import service, get, post, data_io, proxy
from evox.core.queue import get_priority_queue


# Load configuration
try:
    with open("config.toml", "rb") as f:
        config = tomli.load(f)
except FileNotFoundError:
    config = {}

# Service metadata
SERVICE_METADATA = {
    "name": "management_svc",
    "version": "0.1.0",
    "description": "Observer-only management coordinator",
    "type": "management-plane"
}

# Create service
svc = service("management_svc") \
    .port(config.get("port", 8005)) \
    .health("/health") \
    .build()

# Discovered services registry
_discovered_services: Dict[str, Dict[str, Any]] = {}


@svc.on_startup
async def initialize_management():
    """Initialize management service"""
    print("Management service starting...")
    # Start periodic service discovery
    asyncio.create_task(periodic_service_discovery())


async def periodic_service_discovery():
    """Periodically scan for services"""
    while True:
        try:
            await scan_registered_services()
            await asyncio.sleep(30)  # Scan every 30 seconds
        except Exception as e:
            print(f"Service discovery error: {e}")
            await asyncio.sleep(30)


async def scan_registered_services():
    """Scan registered services for health and status"""
    global _discovered_services
    
    # In a real implementation, this would scan service registry
    # For now, we'll simulate with known services
    services_to_check = ["data_intent_svc", "miniapp_svc"]
    
    for service_name in services_to_check:
        try:
            # Try to get health status
            health_status = await proxy.service(service_name).health()
            _discovered_services[service_name] = {
                "status": "reachable",
                "health": health_status,
                "last_checked": time.time()
            }
        except Exception as e:
            _discovered_services[service_name] = {
                "status": "unreachable",
                "error": str(e),
                "last_checked": time.time()
            }


# Service information endpoint
@get("/")
async def service_info():
    """Get management service information and capabilities"""
    return {
        "service": SERVICE_METADATA,
        "endpoints": [
            "/health",
            "/topology",
            "/services",
            "/metrics"
        ],
        "status": "running",
        "timestamp": time.time()
    }


# Enhanced health endpoint
@get("/health")
async def health():
    """Get enhanced health information for management service"""
    # Get queue stats if available
    queue_stats = {}
    try:
        queue = get_priority_queue()
        queue_stats = queue.get_stats()
    except:
        pass
    
    return {
        "status": "healthy", 
        "service": "management_svc",
        "timestamp": time.time(),
        "queue_stats": queue_stats
    }


# Service topology
@get("/topology")
async def topology():
    """Get service topology and relationships"""
    return {
        "services": _discovered_services,
        "relationships": [],  # Would be populated with service dependencies
        "timestamp": time.time()
    }


# Service list
@get("/services")
async def list_services():
    """List all discovered services"""
    return {
        "services": list(_discovered_services.keys()),
        "details": _discovered_services,
        "timestamp": time.time()
    }


# Metrics aggregation
@get("/metrics")
async def aggregate_metrics():
    """Aggregate metrics from all services"""
    aggregated_metrics = {
        "service_count": len(_discovered_services),
        "healthy_services": sum(1 for s in _discovered_services.values() if s.get("status") == "reachable"),
        "unhealthy_services": sum(1 for s in _discovered_services.values() if s.get("status") == "unreachable"),
        "timestamp": time.time()
    }
    
    return aggregated_metrics


# Optional management operations (voluntary, not required)
@post("/services/{service_name}/pause")
async def pause_service(service_name: str):
    """Request service to pause (service may ignore)"""
    try:
        # Try to call optional pause endpoint on service
        result = await proxy.service(service_name).management_pause()
        return {
            "status": "requested",
            "service": service_name,
            "response": result
        }
    except Exception as e:
        return {
            "status": "failed",
            "service": service_name,
            "error": str(e)
        }


@post("/services/{service_name}/scale_hint")
async def scale_hint(service_name: str, hint: dict):
    """Provide scaling hint to service (service may ignore)"""
    try:
        # Try to call optional scale hint endpoint on service
        result = await proxy.service(service_name).management_scale_hint(hint)
        return {
            "status": "hint_sent",
            "service": service_name,
            "hint": hint,
            "response": result
        }
    except Exception as e:
        return {
            "status": "failed",
            "service": service_name,
            "error": str(e)
        }


if __name__ == "__main__":
    svc.run(dev=True)