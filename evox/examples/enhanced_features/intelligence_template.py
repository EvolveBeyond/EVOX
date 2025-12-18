"""
Intelligence Template - Evox Framework Environmental Intelligence Features

This template demonstrates the environmental intelligence features of the enhanced Evox framework:
1. Automatic data understanding and prioritization
2. Requester context adaptation
3. System resource awareness
4. Adaptive concurrency management
"""

from evox import service, Controller, GET, POST, Param, Query, Body, Intent
from evox.core.inject import inject
from evox.core.intelligence import (
    get_environmental_intelligence, 
    understand_data_importance, 
    understand_requester_context,
    auto_adjust_concurrency
)
from pydantic import BaseModel
from typing import Optional
import asyncio


# ================================
# INTELLIGENT DATA MODELS
# ================================

class CriticalDataRequest(BaseModel):
    """Critical data request that should get high priority"""
    data: str
    operation: str
    priority: str = "high"  # This will automatically boost priority


class RegularDataRequest(BaseModel):
    """Regular data request with medium priority"""
    data: str
    operation: str
    priority: str = "medium"


class BackgroundTaskRequest(BaseModel):
    """Background task request with low priority"""
    task_name: str
    parameters: dict
    priority: str = "low"


# ================================
# INTELLIGENT SERVICE WITH ENVIRONMENTAL AWARENESS
# ================================

# Create service with environmental intelligence
service = service("intelligence-template-service") \
    .port(8001) \
    .health("/health") \
    .build()


# Register schema metadata with environmental intelligence
env_intel = get_environmental_intelligence()
env_intel.register_schema(CriticalDataRequest, {
    "importance": "high",
    "caching": False,
    "consistency": "strong"
})
env_intel.register_schema(RegularDataRequest, {
    "importance": "medium",
    "caching": True,
    "ttl": 300
})
env_intel.register_schema(BackgroundTaskRequest, {
    "importance": "low",
    "caching": True,
    "ttl": 3600
})


# ================================
# INTELLIGENT ENDPOINTS
# ================================

@service.endpoint("/process/critical", methods=["POST"])
async def process_critical_data(request: CriticalDataRequest = Body(CriticalDataRequest)):
    """
    Process critical data with automatic high priority
    
    The framework automatically detects this as high priority data based on:
    1. Schema metadata registration
    2. Priority field in the request
    3. Data importance analysis
    """
    # Automatically understand data importance
    priority = understand_data_importance(request)
    
    # Process with high priority
    result = {
        "message": "Processing critical data",
        "data": request.data,
        "operation": request.operation,
        "auto_detected_priority": priority,
        "processing_info": "High priority processing initiated"
    }
    
    return result


@service.endpoint("/process/regular", methods=["POST"])
async def process_regular_data(
    request: RegularDataRequest = Body(RegularDataRequest),
    requester_type: str = Query(str, "user")
):
    """
    Process regular data with context-aware priority
    
    The framework adapts priority based on:
    1. Requester context (admin vs user vs system)
    2. Data importance
    3. System resource status
    """
    # Simulate headers for context analysis
    headers = {"X-Requester-Type": requester_type}
    payload = request.dict()
    
    # Automatically understand requester context
    context = understand_requester_context(headers, payload)
    
    result = {
        "message": "Processing regular data",
        "data": request.data,
        "operation": request.operation,
        "requester_type": requester_type,
        "auto_detected_priority": context["priority"],
        "processing_mode": context["processing_mode"],
        "adaptive_processing": "Context-aware processing applied"
    }
    
    return result


@service.endpoint("/process/background", methods=["POST"])
async def process_background_task(request: BackgroundTaskRequest = Body(BackgroundTaskRequest)):
    """
    Process background task with low priority and resource awareness
    
    The framework automatically:
    1. Assigns low priority to background tasks
    2. Adjusts concurrency based on system resources
    3. Optimizes for resource efficiency
    """
    # Automatically adjust concurrency based on system load
    auto_adjust_concurrency()
    
    # Process with low priority
    result = {
        "message": "Processing background task",
        "task_name": request.task_name,
        "auto_detected_priority": "low",
        "resource_management": "Adaptive concurrency adjustment applied",
        "efficiency_mode": "Resource-optimized processing"
    }
    
    return result


@service.endpoint("/analyze/system", methods=["GET"])
async def analyze_system_status():
    """
    Analyze current system status with environmental intelligence
    
    The framework provides insights into:
    1. Current system load
    2. Resource utilization
    3. Adaptive behavior recommendations
    """
    # Get system intelligence
    load_factor = env_intel.get_system_load_factor()
    
    # Determine system status
    if load_factor > 0.8:
        system_status = "high_load"
        recommendation = "Reduce concurrency, prioritize critical tasks"
    elif load_factor > 0.5:
        system_status = "moderate_load"
        recommendation = "Maintain current processing levels"
    else:
        system_status = "low_load"
        recommendation = "Can increase concurrency for better throughput"
    
    result = {
        "message": "System status analysis",
        "load_factor": round(load_factor, 2),
        "system_status": system_status,
        "recommendation": recommendation,
        "intelligence_features": [
            "Automatic load detection",
            "Adaptive resource management",
            "Context-aware processing"
        ]
    }
    
    return result


# ================================
# INTELLIGENT CONTROLLER
# ================================

@Controller("/api/v1/intelligent", tags=["intelligence"], version="v1")
class IntelligentController:
    """Controller demonstrating environmental intelligence features"""
    
    def __init__(self):
        self.env_intel = get_environmental_intelligence()
    
    @POST("/adaptive-process")
    async def adaptive_process(
        self,
        critical_data: Optional[CriticalDataRequest] = Body(CriticalDataRequest, None),
        regular_data: Optional[RegularDataRequest] = Body(RegularDataRequest, None),
        background_data: Optional[BackgroundTaskRequest] = Body(BackgroundTaskRequest, None)
    ):
        """
        Adaptively process different types of data based on environmental intelligence
        
        The framework automatically:
        1. Determines data importance
        2. Adapts to system load
        3. Optimizes processing strategy
        """
        # Analyze all provided data types
        analysis = {}
        
        if critical_data:
            analysis["critical"] = understand_data_importance(critical_data)
        
        if regular_data:
            analysis["regular"] = understand_data_importance(regular_data)
        
        if background_data:
            analysis["background"] = understand_data_importance(background_data)
        
        # Get system load for adaptive processing
        load_factor = self.env_intel.get_system_load_factor()
        
        # Determine processing strategy
        if load_factor > 0.7:
            strategy = "conservative"
            message = "High system load - prioritizing critical tasks"
        elif load_factor > 0.3:
            strategy = "balanced"
            message = "Moderate system load - balanced processing"
        else:
            strategy = "aggressive"
            message = "Low system load - maximizing throughput"
        
        return {
            "message": "Adaptive processing completed",
            "data_analysis": analysis,
            "system_load": round(load_factor, 2),
            "processing_strategy": strategy,
            "status_message": message,
            "environmental_intelligence": "Fully operational"
        }
    
    @GET("/context-aware")
    @Intent(cacheable=True, ttl=60)
    async def context_aware_endpoint(
        self,
        requester_type: str = Query(str, "user"),
        data_importance: str = Query(str, "medium")
    ):
        """
        Context-aware endpoint that adapts based on requester and data importance
        
        The framework automatically adjusts behavior based on:
        1. Who is making the request
        2. How important the data is
        3. Current system conditions
        """
        # Simulate headers for context analysis
        headers = {"X-Requester-Type": requester_type}
        payload = {"importance": data_importance}
        
        # Analyze context
        context = understand_requester_context(headers, payload)
        
        # Determine response based on context
        if context["priority"] == "high":
            response_message = "High-priority response with immediate processing"
        elif context["priority"] == "low":
            response_message = "Low-priority response with deferred processing"
        else:
            response_message = "Standard response with normal processing"
        
        return {
            "message": "Context-aware processing",
            "requester_type": requester_type,
            "data_importance": data_importance,
            "auto_detected_priority": context["priority"],
            "response_strategy": response_message,
            "processing_mode": context["processing_mode"],
            "cache_enabled": context["caching"]
        }


# Controllers are automatically registered when service is built
# service.register_controller(IntelligentController)


# ================================
# PERIODIC INTELLIGENCE UPDATES
# ================================

@service.background_task(interval=30)
async def update_intelligence_metrics():
    """Periodically update intelligence metrics and adjust system behavior"""
    print("🧠 Updating environmental intelligence metrics...")
    
    # Auto-adjust concurrency based on current system load
    auto_adjust_concurrency()
    
    # Log current system status
    env_intel = get_environmental_intelligence()
    load_factor = env_intel.get_system_load_factor()
    print(f"📊 Current system load: {round(load_factor * 100, 1)}%")


# ================================
# MAIN ENTRY POINT
# ================================

if __name__ == "__main__":
    print("🚀 Starting Intelligence Template Service...")
    print("🧠 Environmental Intelligence Features Enabled")
    print("⚡ Ready for context-aware, adaptive processing")
    
    # Run the service
    service.run(dev=True)