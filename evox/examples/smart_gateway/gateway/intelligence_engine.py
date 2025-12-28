"""
Intelligence Engine for Smart Gateway
====================================

This module implements the intelligence capabilities of the smart gateway,
including environmental awareness, load detection, and adaptive behavior.
"""

import asyncio
import psutil
import time
from typing import Dict, Any
from enum import Enum
from dataclasses import dataclass
from evox.core.intelligence import SystemMonitor
from evox.core.queue import PriorityAwareQueue


class RequestPriority(Enum):
    """Priority levels for requests."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class SystemMetrics:
    """System metrics for intelligence decisions."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: float
    active_requests: int
    queue_size: int
    timestamp: float


class IntelligenceEngine:
    """
    Intelligence Engine for Environmental Awareness and Adaptive Behavior
    
    This engine monitors system resources, detects environmental conditions,
    and makes adaptive decisions to protect system resources while
    prioritizing critical operations.
    """
    
    def __init__(self):
        self._system_monitor = SystemMonitor()
        self._priority_queue = PriorityAwareQueue()
        self._resource_thresholds = {
            "cpu": 80.0,  # percentage
            "memory": 85.0,  # percentage
            "disk": 90.0,  # percentage
            "load": 5.0,  # load average
        }
        self._active_requests = 0
        self._metrics_history = []
        self._is_protecting_resources = False
        self._last_adjustment = 0
        self._concurrency_limit = 100  # default concurrency limit
    
    async def get_system_metrics(self) -> SystemMetrics:
        """
        Get current system metrics for intelligence decisions.
        
        Returns:
            Current system metrics including CPU, memory, disk usage, etc.
        """
        # Get system metrics using psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
        
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            load_average=load_avg,
            active_requests=self._active_requests,
            queue_size=self._priority_queue.size(),
            timestamp=time.time()
        )
        
        # Store in history for trend analysis
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > 100:  # Keep last 100 metrics
            self._metrics_history.pop(0)
        
        return metrics
    
    def analyze_environment(self, metrics: SystemMetrics) -> Dict[str, Any]:
        """
        Analyze the current environment and make intelligence decisions.
        
        Args:
            metrics: Current system metrics
            
        Returns:
            Analysis results with environmental intelligence
        """
        analysis = {
            "system_load": "normal",
            "resource_pressure": "low",
            "recommendation": "continue_normal_operations",
            "load_shedding_needed": False,
            "priority_adjustment_needed": False,
            "resource_protection_needed": False
        }
        
        # Check CPU pressure
        if metrics.cpu_percent > self._resource_thresholds["cpu"]:
            analysis["system_load"] = "high"
            analysis["resource_pressure"] = "high"
            analysis["resource_protection_needed"] = True
            
        # Check memory pressure
        if metrics.memory_percent > self._resource_thresholds["memory"]:
            analysis["system_load"] = "high"
            analysis["resource_pressure"] = "high"
            analysis["resource_protection_needed"] = True
            analysis["load_shedding_needed"] = True
        
        # Check disk pressure
        if metrics.disk_percent > self._resource_thresholds["disk"]:
            analysis["resource_pressure"] = "high"
            analysis["resource_protection_needed"] = True
        
        # Check load average
        if metrics.load_average > self._resource_thresholds["load"]:
            analysis["system_load"] = "very_high"
            analysis["resource_pressure"] = "high"
            analysis["load_shedding_needed"] = True
            analysis["priority_adjustment_needed"] = True
        
        # Check queue size
        if metrics.queue_size > 50:  # High queue size indicates pressure
            analysis["system_load"] = "high" if analysis["system_load"] == "normal" else analysis["system_load"]
            analysis["priority_adjustment_needed"] = True
        
        # Determine recommendation based on analysis
        if analysis["resource_protection_needed"]:
            if analysis["load_shedding_needed"]:
                analysis["recommendation"] = "protect_resources_with_load_shedding"
            else:
                analysis["recommendation"] = "protect_resources_with_concurrency_limit"
        elif analysis["priority_adjustment_needed"]:
            analysis["recommendation"] = "adjust_priority_handling"
        else:
            analysis["recommendation"] = "continue_normal_operations"
        
        return analysis
    
    async def auto_adjust_concurrency(self) -> int:
        """
        Automatically adjust concurrency based on system load.
        
        Returns:
            Recommended concurrency limit
        """
        current_time = time.time()
        
        # Don't adjust too frequently
        if current_time - self._last_adjustment < 5:  # 5 seconds minimum between adjustments
            return self._concurrency_limit
        
        metrics = await self.get_system_metrics()
        analysis = self.analyze_environment(metrics)
        
        # Adjust concurrency based on system load
        if analysis["resource_protection_needed"]:
            if analysis["system_load"] == "very_high":
                self._concurrency_limit = max(5, int(self._concurrency_limit * 0.3))  # Reduce to 30%
            elif analysis["system_load"] == "high":
                self._concurrency_limit = max(10, int(self._concurrency_limit * 0.6))  # Reduce to 60%
        else:
            # Gradually increase concurrency when load is low
            if metrics.cpu_percent < 50 and metrics.memory_percent < 60:
                self._concurrency_limit = min(200, int(self._concurrency_limit * 1.1))  # Increase by 10%
        
        self._last_adjustment = current_time
        
        # Update the system monitor with new limit
        await self._system_monitor.set_concurrency_limit(self._concurrency_limit)
        
        return self._concurrency_limit
    
    def calculate_request_priority(self, request_data: Dict[str, Any]) -> RequestPriority:
        """
        Calculate the priority of a request based on environmental intelligence.
        
        Args:
            request_data: Data about the incoming request
            
        Returns:
            Calculated priority level for the request
        """
        # Default to normal priority
        priority = RequestPriority.NORMAL
        
        # Check for critical indicators in request
        if request_data.get("priority") == "critical":
            priority = RequestPriority.CRITICAL
        elif request_data.get("priority") == "high":
            priority = RequestPriority.HIGH
        elif request_data.get("priority") == "low":
            priority = RequestPriority.LOW
        else:
            # Analyze request content for intelligence-based priority
            if self._is_critical_request(request_data):
                priority = RequestPriority.CRITICAL
            elif self._is_high_importance_request(request_data):
                priority = RequestPriority.HIGH
            elif self._is_low_priority_request(request_data):
                priority = RequestPriority.LOW
        
        return priority
    
    def _is_critical_request(self, request_data: Dict[str, Any]) -> bool:
        """Determine if a request is critical based on content."""
        # Check for critical endpoints or operations
        path = request_data.get("path", "")
        method = request_data.get("method", "").upper()
        
        critical_indicators = [
            "/health" in path,
            "/emergency" in path,
            method == "POST" and "/payment" in path,
            method == "POST" and "/auth" in path,
            request_data.get("is_urgent", False)
        ]
        
        return any(critical_indicators)
    
    def _is_high_importance_request(self, request_data: Dict[str, Any]) -> bool:
        """Determine if a request is high importance based on content."""
        path = request_data.get("path", "")
        user_role = request_data.get("user_role", "user")
        
        high_importance_indicators = [
            user_role in ["admin", "superuser"],
            "/api/v1/admin" in path,
            "/api/v1/user/premium" in path
        ]
        
        return any(high_importance_indicators)
    
    def _is_low_priority_request(self, request_data: Dict[str, Any]) -> bool:
        """Determine if a request is low priority based on content."""
        path = request_data.get("path", "")
        
        low_priority_indicators = [
            "/metrics" in path,
            "/analytics" in path,
            "/logs" in path,
            request_data.get("is_background", False)
        ]
        
        return any(low_priority_indicators)
    
    async def process_request_intelligently(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request with intelligence-based priority and resource management.
        
        Args:
            request_data: Data about the incoming request
            
        Returns:
            Processed result with intelligence-based handling
        """
        # Calculate request priority
        priority = self.calculate_request_priority(request_data)
        
        # Get current system metrics
        metrics = await self.get_system_metrics()
        analysis = self.analyze_environment(metrics)
        
        # Apply load shedding if needed
        if analysis["load_shedding_needed"] and priority == RequestPriority.LOW:
            return {
                "status": "rejected",
                "reason": "load_shedding",
                "message": "System under high load, low priority request rejected"
            }
        
        # Add request to priority queue
        queue_item = {
            "request_data": request_data,
            "priority": priority.value,
            "timestamp": time.time()
        }
        
        await self._priority_queue.enqueue(queue_item, priority.value)
        
        # Adjust concurrency if needed
        if analysis["priority_adjustment_needed"]:
            await self.auto_adjust_concurrency()
        
        # Process the request based on priority
        result = await self._process_request_with_priority(queue_item)
        
        return result
    
    async def _process_request_with_priority(self, queue_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request according to its priority level.
        
        Args:
            queue_item: Request item from the priority queue
            
        Returns:
            Processed result
        """
        request_data = queue_item["request_data"]
        priority = queue_item["priority"]
        
        # Simulate processing based on priority
        if priority == "critical":
            # Critical requests get immediate processing
            await asyncio.sleep(0.1)  # Simulate fast processing
            result = {
                "status": "success",
                "priority": "critical",
                "processed_immediately": True,
                "response_time": 0.1
            }
        elif priority == "high":
            # High priority requests get preferential treatment
            await asyncio.sleep(0.2)  # Simulate processing
            result = {
                "status": "success", 
                "priority": "high",
                "processed_with_priority": True,
                "response_time": 0.2
            }
        elif priority == "normal":
            # Normal requests get standard processing
            await asyncio.sleep(0.3)  # Simulate processing
            result = {
                "status": "success",
                "priority": "normal", 
                "response_time": 0.3
            }
        else:  # low
            # Low priority requests may experience delays
            await asyncio.sleep(0.5)  # Simulate slower processing
            result = {
                "status": "success",
                "priority": "low",
                "processed_when_resources_available": True,
                "response_time": 0.5
            }
        
        return result
    
    async def get_intelligence_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive intelligence report about the system.
        
        Returns:
            Intelligence report with system analysis and recommendations
        """
        metrics = await self.get_system_metrics()
        analysis = self.analyze_environment(metrics)
        
        report = {
            "timestamp": metrics.timestamp,
            "current_metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_percent": metrics.disk_percent,
                "load_average": metrics.load_average,
                "active_requests": metrics.active_requests,
                "queue_size": metrics.queue_size
            },
            "environmental_analysis": analysis,
            "current_concurrency_limit": self._concurrency_limit,
            "is_protecting_resources": self._is_protecting_resources,
            "recommendations": [
                f"Current system load: {analysis['system_load']}",
                f"Resource pressure: {analysis['resource_pressure']}",
                f"Action recommended: {analysis['recommendation']}"
            ]
        }
        
        return report


# Global intelligence engine instance
intelligence_engine = IntelligenceEngine()