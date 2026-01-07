"""
Monitoring Service - Pluggable Metrics & Monitoring Module for EVOX Framework

This service implements metrics collection and monitoring functionality 
that was moved out of the core. It subscribes to lifecycle events to 
collect and analyze system metrics.
"""

from evoid import service, get, post, Body, Intent
from evoid.core.lifecycle import (
    LifecycleEvent, 
    subscribe_to_event, 
    EventContext,
    on_service_init,
    pre_dispatch,
    post_dispatch,
    on_data_io_error,
    on_system_stress
)
from pydantic import BaseModel
from typing import Annotated, Dict, Any, Optional, List
import time
import psutil
from datetime import datetime
from collections import defaultdict, deque
import asyncio


class Metric(BaseModel):
    """Model for a metric entry"""
    name: str
    value: float
    timestamp: str
    tags: Optional[Dict[str, str]] = None


class SystemMetrics(BaseModel):
    """Model for system metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, float]
    request_count: int
    error_count: int
    avg_response_time: float
    timestamp: str


class MonitorService:
    """Service for handling monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 values
        self.request_count = 0
        self.error_count = 0
        self.response_times = deque(maxlen=1000)
        self.start_time = time.time()
        
        # Track request timing
        self.pending_requests = {}
        
        # System metrics
        self.system_metrics = SystemMetrics(
            cpu_percent=0.0,
            memory_percent=0.0,
            disk_usage_percent=0.0,
            network_io={"bytes_sent": 0.0, "bytes_recv": 0.0},
            request_count=0,
            error_count=0,
            avg_response_time=0.0,
            timestamp=datetime.now().isoformat()
        )
    
    async def collect_system_metrics(self):
        """Collect system metrics"""
        self.system_metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
        self.system_metrics.memory_percent = psutil.virtual_memory().percent
        self.system_metrics.disk_usage_percent = psutil.disk_usage('/').percent
        
        # Network I/O
        net_io = psutil.net_io_counters()
        self.system_metrics.network_io = {
            "bytes_sent": float(net_io.bytes_sent),
            "bytes_recv": float(net_io.bytes_recv)
        }
        
        # Update counts
        self.system_metrics.request_count = self.request_count
        self.system_metrics.error_count = self.error_count
        
        # Calculate average response time
        if self.response_times:
            avg_time = sum(self.response_times) / len(self.response_times)
            self.system_metrics.avg_response_time = avg_time
        else:
            self.system_metrics.avg_response_time = 0.0
            
        self.system_metrics.timestamp = datetime.now().isoformat()
        
        # Store in metrics history
        self.metrics_history["cpu_percent"].append({
            "value": self.system_metrics.cpu_percent,
            "timestamp": self.system_metrics.timestamp
        })
        self.metrics_history["memory_percent"].append({
            "value": self.system_metrics.memory_percent,
            "timestamp": self.system_metrics.timestamp
        })
    
    async def track_request_start(self, request_id: str):
        """Track when a request starts"""
        self.pending_requests[request_id] = time.time()
        self.request_count += 1
    
    async def track_request_end(self, request_id: str, success: bool = True):
        """Track when a request ends and calculate response time"""
        start_time = self.pending_requests.pop(request_id, None)
        if start_time:
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            
            # Add to metrics history
            self.metrics_history["response_time"].append({
                "value": response_time,
                "timestamp": datetime.now().isoformat(),
                "success": success
            })
    
    async def track_error(self):
        """Track an error occurrence"""
        self.error_count += 1
        self.metrics_history["errors"].append({
            "value": 1,
            "timestamp": datetime.now().isoformat()
        })
    
    async def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        await self.collect_system_metrics()
        return self.system_metrics
    
    async def get_metric_history(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric"""
        history = list(self.metrics_history[metric_name])[-limit:]
        return history
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get all available metrics"""
        await self.collect_system_metrics()
        return {
            "system_metrics": self.system_metrics,
            "uptime": time.time() - self.start_time,
            "metrics_available": list(self.metrics_history.keys()),
            "total_requests": self.request_count,
            "total_errors": self.error_count
        }


# Initialize the service
mon_svc = service("monitor-service").port(8007).build()
monitor_service = MonitorService()


# Subscribe to lifecycle events
async def handle_service_init(context: EventContext):
    await monitor_service.collect_system_metrics()

async def handle_pre_dispatch(context: EventContext):
    # Generate a unique request ID and track it
    request_id = f"req_{int(time.time() * 1000000)}"
    if context.request_info:
        context.request_info["request_id"] = request_id
    await monitor_service.track_request_start(request_id)

async def handle_post_dispatch(context: EventContext):
    request_id = context.request_info.get("request_id") if context.request_info else None
    if request_id:
        await monitor_service.track_request_end(request_id, success=True)

async def handle_data_io_error(context: EventContext):
    await monitor_service.track_error()

async def handle_system_stress(context: EventContext):
    # Collect metrics when system is under stress
    await monitor_service.collect_system_metrics()


# Subscribe to all relevant events
subscribe_to_event(LifecycleEvent.ON_SERVICE_INIT, handle_service_init, "monitor-service")
subscribe_to_event(LifecycleEvent.PRE_DISPATCH, handle_pre_dispatch, "monitor-service")
subscribe_to_event(LifecycleEvent.POST_DISPATCH, handle_post_dispatch, "monitor-service")
subscribe_to_event(LifecycleEvent.ON_DATA_IO_ERROR, handle_data_io_error, "monitor-service")
subscribe_to_event(LifecycleEvent.ON_SYSTEM_STRESS, handle_system_stress, "monitor-service")


# API endpoints for monitoring
@get("/metrics")
async def get_metrics():
    """Get current system metrics"""
    metrics = await monitor_service.get_all_metrics()
    return metrics


@get("/metrics/system")
async def get_system_metrics():
    """Get current system metrics only"""
    system_metrics = await monitor_service.get_current_metrics()
    return system_metrics


@get("/metrics/history/{metric_name}")
async def get_metric_history(metric_name: str, limit: int = 50):
    """Get historical data for a specific metric"""
    history = await monitor_service.get_metric_history(metric_name, limit)
    return {"metric": metric_name, "history": history, "count": len(history)}


@get("/monitor/health")
async def monitor_health():
    """Health check for the monitoring service"""
    metrics = await monitor_service.get_current_metrics()
    return {
        "status": "healthy",
        "service": "monitor-service",
        "cpu_percent": metrics.cpu_percent,
        "memory_percent": metrics.memory_percent
    }


@post("/monitor/alerts")
async def create_alert(config: Annotated[Dict[str, Any], Body]):
    """Create monitoring alerts"""
    # In a real implementation, this would set up alerting rules
    return {"status": "alert_configured", "config": config}


# Background task to periodically collect metrics
@mon_svc.background_task(interval=10)
async def collect_metrics():
    """Background task to periodically collect system metrics"""
    await monitor_service.collect_system_metrics()


# Example startup handler
@mon_svc.on_startup
async def startup():
    print("Monitor service started")
    # Trigger service init event
    await on_service_init("monitor-service", monitor_service)
    
    # Start collecting metrics
    await monitor_service.collect_system_metrics()


# Example shutdown handler
@mon_svc.on_shutdown
async def shutdown():
    print("Monitor service stopped")


if __name__ == "__main__":
    mon_svc.run(dev=True)