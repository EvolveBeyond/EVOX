"""
Smart Gateway Service
===================

An intelligence-driven gateway demonstrating:
- SystemMonitor detecting high load and triggering auto_adjust_concurrency()
- Priority Queues handling CRITICAL vs LOW priority requests
- Environmental intelligence for adaptive behavior
- Resource protection mechanisms

This example shows how to build an adaptive system that protects its own resources.
"""

import asyncio
from typing import Dict, Any
from pydantic import BaseModel, Field
from evox import service, get, post, Body, Query
from evox.core.inject import HealthAwareInject
from evox.core.intelligence import SystemMonitor
from evox.core.queue import PriorityAwareQueue
from ..gateway.intelligence_engine import intelligence_engine


class RequestData(BaseModel):
    """Model for incoming request data."""
    path: str = Field(..., description="Request path")
    method: str = Field(..., description="HTTP method")
    user_role: str = Field(default="user", description="User role")
    is_urgent: bool = Field(default=False, description="Is this an urgent request?")
    is_background: bool = Field(default=False, description="Is this a background request?")
    priority: str | None = Field(None, description="Explicit priority override")


class GatewayResponse(BaseModel):
    """Model for gateway responses."""
    status: str
    priority: str | None = None
    processed_immediately: bool | None = None
    response_time: float | None = None
    message: str | None = None


class SmartGatewayService:
    """
    Smart Gateway Service with Intelligence-Driven Operations
    
    This service demonstrates how environmental intelligence can be used
    to make adaptive decisions about request handling, resource allocation,
    and priority management to protect system resources.
    """
    
    def __init__(self):
        self._system_monitor = SystemMonitor()
        self._priority_queue = PriorityAwareQueue()
        self._intelligence_engine = intelligence_engine
        self._request_counter = 0
        self._initialized = False
    
    async def initialize(self):
        """Initialize the smart gateway service."""
        if not self._initialized:
            await self._system_monitor.initialize()
            self._initialized = True
    
    async def handle_request(self, request_data: RequestData) -> GatewayResponse:
        """
        Handle an incoming request with intelligence-based processing.
        
        This method demonstrates how the gateway uses environmental intelligence
        to make decisions about request handling, priority assignment, and
        resource allocation.
        """
        await self.initialize()
        
        # Convert request data to dict for intelligence engine
        request_dict = {
            "path": request_data.path,
            "method": request_data.method,
            "user_role": request_data.user_role,
            "is_urgent": request_data.is_urgent,
            "is_background": request_data.is_background,
            "priority": request_data.priority
        }
        
        # Process the request intelligently
        result = await self._intelligence_engine.process_request_intelligently(request_dict)
        
        # Return as GatewayResponse
        return GatewayResponse(
            status=result.get("status", "unknown"),
            priority=result.get("priority"),
            processed_immediately=result.get("processed_immediately"),
            response_time=result.get("response_time"),
            message=result.get("message")
        )
    
    async def get_intelligence_report(self) -> Dict[str, Any]:
        """Get the intelligence report from the engine."""
        return await self._intelligence_engine.get_intelligence_report()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get the current system status."""
        metrics = await self._intelligence_engine.get_system_metrics()
        return {
            "system_metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_percent": metrics.disk_percent,
                "load_average": metrics.load_average,
                "active_requests": metrics.active_requests,
                "queue_size": metrics.queue_size
            },
            "service_status": {
                "initialized": self._initialized,
                "request_counter": self._request_counter
            },
            "intelligence_status": {
                "concurrency_limit": self._intelligence_engine._concurrency_limit,
                "is_protecting_resources": self._intelligence_engine._is_protecting_resources
            }
        }
    
    async def adjust_concurrency(self) -> Dict[str, Any]:
        """Manually trigger concurrency adjustment."""
        new_limit = await self._intelligence_engine.auto_adjust_concurrency()
        return {
            "status": "success",
            "new_concurrency_limit": new_limit
        }


# Initialize the service instance
gateway_service = SmartGatewayService()
HealthAwareInject.register_instance("smart_gateway_service", gateway_service)


@get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for the smart gateway."""
    return {
        "status": "healthy",
        "service": "smart-gateway",
        "features": ["intelligence-engine", "priority-queues", "adaptive-concurrency"]
    }


@post("/process")
async def process_request(
    request_data: RequestData = Body(..., description="Request data to process")
) -> GatewayResponse:
    """
    Process a request with intelligence-based priority handling.
    
    Demonstrates how the gateway uses environmental intelligence to
    make adaptive decisions about request handling and resource allocation.
    """
    service = HealthAwareInject["SmartGatewayService"]()
    
    # Increment request counter
    gateway_service._request_counter += 1
    
    result = await service.handle_request(request_data)
    return result


@get("/intelligence/report")
async def get_intelligence_report() -> Dict[str, Any]:
    """
    Get the intelligence report with system analysis and recommendations.
    
    This endpoint demonstrates the environmental awareness capabilities
    of the smart gateway.
    """
    service = HealthAwareInject["SmartGatewayService"]()
    return await service.get_intelligence_report()


@get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get the current system status.
    
    Shows real-time metrics about system resources, request handling,
    and intelligence engine status.
    """
    service = HealthAwareInject["SmartGatewayService"]()
    return await service.get_system_status()


@post("/adjust-concurrency")
async def adjust_concurrency_endpoint() -> Dict[str, Any]:
    """
    Manually trigger concurrency adjustment.
    
    This endpoint demonstrates how the system can adapt its concurrency
    limits based on environmental conditions.
    """
    service = HealthAwareInject["SmartGatewayService"]()
    return await service.adjust_concurrency()


@get("/simulate-load")
async def simulate_load(
    requests: int = Query(10, description="Number of requests to simulate")
) -> Dict[str, Any]:
    """
    Simulate load on the system to trigger intelligence behaviors.
    
    This endpoint helps demonstrate how the system responds to
    different load conditions.
    """
    # Simulate multiple requests to trigger load
    tasks = []
    for i in range(requests):
        request_data = RequestData(
            path=f"/api/test/{i}",
            method="GET",
            user_role="user",
            is_urgent=(i % 5 == 0)  # Every 5th request is urgent
        )
        tasks.append(gateway_service.handle_request(request_data))
    
    results = await asyncio.gather(*tasks)
    
    # Trigger a concurrency adjustment after simulating load
    await gateway_service.adjust_concurrency()
    
    return {
        "status": "load_simulation_complete",
        "requests_processed": len(results),
        "message": f"Simulated {requests} requests to test intelligence behaviors"
    }


# Create and configure the service using EVOX
gateway_svc = service("smart-gateway") \
    .port(8003) \
    .build()


async def demonstrate_intelligence_features():
    """
    Demonstrate the intelligence features of the smart gateway.
    """
    print("🧠 EVOX Smart Gateway - Intelligence-Driven System")
    print("=" * 55)
    
    # Initialize the service
    await gateway_service.initialize()
    
    print("\n🎯 Intelligence Features Demonstrated:")
    print("• Environmental awareness with system monitoring")
    print("• Adaptive concurrency adjustment based on load")
    print("• Priority queue handling for different request types")
    print("• Resource protection during high load")
    print("• Load shedding for non-critical requests")
    
    print("\n💡 Intelligence-Driven Decisions:")
    print("• Automatic priority assignment based on request content")
    print("• Dynamic concurrency limits based on system metrics")
    print("• Load shedding when resources are under pressure")
    print("• Critical request protection during high load")
    
    print("\n📊 System Monitoring Capabilities:")
    status = await gateway_service.get_system_status()
    metrics = status["system_metrics"]
    print(f"  CPU Usage: {metrics['cpu_percent']}%")
    print(f"  Memory Usage: {metrics['memory_percent']}%")
    print(f"  Active Requests: {metrics['active_requests']}")
    print(f"  Queue Size: {metrics['queue_size']}")
    
    print("\n📋 Intelligence Engine Status:")
    report = await gateway_service.get_intelligence_report()
    analysis = report["environmental_analysis"]
    print(f"  System Load: {analysis['system_load']}")
    print(f"  Resource Pressure: {analysis['resource_pressure']}")
    print(f"  Current Action: {analysis['recommendation']}")
    
    print("\n✨ Built with Python 3.13+ Modern Syntax:")
    print("• Union syntax: X | Y instead of Union[X, Y]")
    print("• Enhanced type annotations")
    print("• Modern async/await patterns")
    
    print("\n✅ Smart Gateway ready to run with: gateway_svc.run(dev=True)")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_intelligence_features())
    
    # Uncomment the following line to run the service
    # gateway_svc.run(dev=True)