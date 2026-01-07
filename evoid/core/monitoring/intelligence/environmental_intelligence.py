"""
Environmental Intelligence - Framework intelligence for automatic context understanding

This module provides environmental intelligence features that allow the framework to:
1. Automatically understand data schemas and their importance
2. Adapt to requester context and requirements
3. Prioritize requests based on system understanding
4. Minimize boilerplate for developers

Design Philosophy:
- Zero-config intelligence: Works automatically without explicit configuration
- Context-aware adaptation: Adjusts behavior based on runtime conditions
- Resource-aware optimization: Considers system load for optimal performance
- Developer-friendly API: Clean, intuitive interfaces for common operations
"""

from typing import Any
from pydantic import BaseModel
import psutil
import asyncio
# Local imports to avoid circular dependencies
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...infrastructure.queue.priority_queue import get_priority_queue, PriorityLevel
    from ...data.intents.intent_system import extract_intents, model_intent_score, Intent, get_intent_registry
from enum import Enum
import logging


class SystemStatus(str, Enum):
    """
    System status enum for resource monitoring.
    
    Rationale: Provides clear, standardized system health states that can be used
    by the framework to make intelligent decisions about request handling.
    """
    GREEN = "green"
    """System is healthy and operating normally"""
    
    YELLOW = "yellow"
    """System is under moderate stress, consider load shedding"""
    
    RED = "red"
    """System is under critical stress, only critical requests allowed"""


class EnvironmentalIntelligence:
    """
    Environmental Intelligence system that provides automatic context understanding
    
    This system enables the framework to automatically understand:
    - Data schemas and their importance
    - Requester context and requirements
    - System resource status
    - Optimal request prioritization
    
    Design Rationale:
    - Centralized intelligence: Single source of truth for environmental understanding
    - Schema-driven decisions: Leverages data models for smarter processing
    - Adaptive behavior: Responds to changing system conditions in real-time
    - Minimal developer overhead: Intelligence works automatically behind the scenes
    """
    
    def __init__(self):
        self._schema_metadata = {}
        self._requester_profiles = {}
        self._system_monitor = SystemMonitor()
    
    def register_schema(self, schema_class: type, metadata: dict[str, Any]):
        """
        Register a schema with metadata for automatic understanding
        
        Args:
            schema_class: The Pydantic model class
            metadata: Metadata about the schema including importance, caching, etc.
        
        Rationale:
            Enables the framework to make intelligent decisions based on data schema
            without requiring explicit configuration in each endpoint.
        """
        schema_name = schema_class.__name__
        self._schema_metadata[schema_name] = metadata
    
    def get_schema_importance(self, schema_instance: BaseModel) -> str:
        """
        Determine the importance level of a schema instance
        
        Args:
            schema_instance: Instance of a Pydantic model
            
        Returns:
            Priority level ("high", "medium", "low")
        
        Rationale:
            Automatic priority determination reduces boilerplate and ensures
            consistent prioritization across the system based on data importance.
        """
        schema_name = schema_instance.__class__.__name__
        
        # Check registered metadata
        if schema_name in self._schema_metadata:
            metadata = self._schema_metadata[schema_name]
            if 'importance' in metadata:
                return metadata['importance']
        
        # Check schema fields for importance indicators
        if hasattr(schema_instance, 'priority') and schema_instance.priority:
            priority = schema_instance.priority.lower()
            if priority in ['high', 'medium', 'low']:
                return priority
        
        # Default to medium importance
        return "medium"
    
    def analyze_requester_context(self, headers: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze requester context to determine appropriate handling
        
        Args:
            headers: Request headers
            payload: Request payload
            
        Returns:
            Context analysis including priority, caching, and processing hints
        
        Rationale:
            Context-aware processing allows the framework to adapt behavior based on
            who is making the request, enabling better resource allocation and UX.
        """
        context = {
            "priority": "medium",
            "caching": True,
            "processing_mode": "standard"
        }
        
        # Check for requester type in headers
        if 'X-Requester-Type' in headers:
            requester_type = headers['X-Requester-Type'].lower()
            if requester_type == 'admin':
                context["priority"] = "high"
                context["processing_mode"] = "immediate"
            elif requester_type == 'system':
                context["priority"] = "low"
                context["processing_mode"] = "background"
        
        # Check for explicit priority in headers or payload
        if 'X-Priority' in headers:
            priority = headers['X-Priority'].lower()
            if priority in ['high', 'medium', 'low']:
                context["priority"] = priority
        elif 'priority' in payload:
            priority = payload['priority'].lower()
            if priority in ['high', 'medium', 'low']:
                context["priority"] = priority
        
        return context
    
    def get_system_load_factor(self) -> float:
        """
        Get system load factor for adaptive concurrency management
        
        Returns:
            Load factor between 0.0 (idle) and 1.0 (maximum load)
        """
        return self._system_monitor.get_load_factor()
    
    def get_current_system_status(self) -> SystemStatus:
        """
        Get the current system status based on resource utilization.
        
        Rationale:
            Provides a high-level system health status that can be used by
            other components to make intelligent decisions about request handling.
        
        Returns:
            SystemStatus enum value indicating current system health
        """
        return self._system_monitor.get_system_status()


class SystemMonitor:
    """Monitor system resources for adaptive behavior
    
    Rationale:
        Real-time system monitoring enables the framework to adapt concurrency
        and processing strategies based on actual resource availability.
    """
    
    def __init__(self):
        self._last_check = 0
        self._cached_load = 0.0
        self._cached_status = SystemStatus.GREEN
        self._cache_duration = 1.0  # Cache for 1 second
        self._cpu_threshold_yellow = 80.0  # CPU % for yellow status
        self._cpu_threshold_red = 95.0     # CPU % for red status
        self._memory_threshold_yellow = 80.0  # Memory % for yellow status
        self._memory_threshold_red = 95.0     # Memory % for red status
    
    def get_load_factor(self) -> float:
        """
        Get current system load factor
        
        Returns:
            Load factor between 0.0 (idle) and 1.0 (maximum load)
        """
        current_time = asyncio.get_event_loop().time()
        if current_time - self._last_check < self._cache_duration:
            return self._cached_load
        
        # Collect system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        # Normalize to 0.0-1.0 range
        cpu_load = cpu_percent / 100.0
        memory_load = memory_percent / 100.0
        
        # Take the maximum as the load factor
        load_factor = max(cpu_load, memory_load)
        
        # Update cache
        self._cached_load = load_factor
        self._last_check = current_time
        
        return load_factor
    
    def get_system_status(self) -> SystemStatus:
        """
        Get the current system status based on resource utilization.
        
        Rationale:
            Provides a simple enum-based status that can be used by other
            components to make decisions about request handling and resource allocation.
        
        Returns:
            SystemStatus enum value
        """
        current_time = asyncio.get_event_loop().time()
        if current_time - self._last_check < self._cache_duration:
            return self._cached_status
        
        # Get current system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        # Determine status based on thresholds
        max_usage = max(cpu_percent, memory_percent)
        
        if max_usage >= self._memory_threshold_red or max_usage >= self._cpu_threshold_red:
            status = SystemStatus.RED
        elif max_usage >= self._memory_threshold_yellow or max_usage >= self._cpu_threshold_yellow:
            status = SystemStatus.YELLOW
        else:
            status = SystemStatus.GREEN
        
        # Update cache
        self._cached_status = status
        self._cached_load = max_usage / 100.0  # Also update load factor
        self._last_check = current_time
        
        return status


# Global environmental intelligence instance
_env_intelligence = EnvironmentalIntelligence()


def get_environmental_intelligence() -> EnvironmentalIntelligence:
    """
    Get the global environmental intelligence instance
    
    Returns:
        EnvironmentalIntelligence instance
    """
    return _env_intelligence


def get_current_context_status() -> SystemStatus:
    """
    Get the current system status based on resource utilization.
    
    Rationale:
        Provides a simple function for other components to check the
        current system health status and make intelligent decisions.
    
    Returns:
        SystemStatus enum value indicating current system health
    """
    return _env_intelligence.get_current_system_status()


def auto_adjust_concurrency():
    """
    Automatically adjust concurrency based on system load
    
    This function should be called periodically to adjust queue concurrency limits
    based on current system resource usage.
    """
    # Import locally to avoid circular import
    from ...infrastructure.queue.priority_queue import get_priority_queue
    
    env_intel = get_environmental_intelligence()
    load_factor = env_intel.get_system_load_factor()
    
    # Adjust queue concurrency based on load
    queue = get_priority_queue()
    queue.adjust_concurrency_based_on_resources(
        cpu_usage=load_factor,
        memory_usage=load_factor
    )


# Convenience functions for common intelligence operations
def understand_data_importance(data: BaseModel | dict[str, Any]) -> str:
    """
    Understand the importance of data automatically
    
    Args:
        data: Data to analyze (Pydantic model or dict)
        
    Returns:
        Priority level ("high", "medium", "low")
    
    Rationale:
        Provides a simple interface for developers to leverage environmental
        intelligence without needing to interact with internal systems directly.
    """
    env_intel = get_environmental_intelligence()
    
    if isinstance(data, BaseModel):
        return env_intel.get_schema_importance(data)
    elif isinstance(data, dict):
        # Check for priority field in dict
        if 'priority' in data:
            priority = data['priority'].lower()
            if priority in ['high', 'medium', 'low']:
                return priority
    
    # Default to medium importance
    return "medium"


def understand_requester_context(headers: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """
    Understand requester context automatically
    
    Args:
        headers: Request headers
        payload: Request payload
        
    Returns:
        Context analysis including priority and processing hints
    """
    env_intel = get_environmental_intelligence()
    return env_intel.analyze_requester_context(headers, payload)


def analyze_schema_intent(schema: type[BaseModel]) -> float:
    """
    Analyze the declared intents of a schema and calculate an importance score.
    
    Rationale:
        This function enables the framework to understand the developer's intent
        for data handling and apply appropriate processing strategies based on
        the declared intents (critical, sensitive, ephemeral, lazy).

    Args:
        schema: The Pydantic model class to analyze
        
    Returns:
        A numerical score representing the overall importance of the schema
    """
    # Import locally to avoid circular import
    from ...data.intents.intent_system import model_intent_score
    return model_intent_score(schema)


# Export public API
__all__ = [
    "EnvironmentalIntelligence",
    "get_environmental_intelligence",
    "auto_adjust_concurrency",
    "understand_data_importance",
    "understand_requester_context",
    "analyze_schema_intent",
    "SystemStatus",
    "get_current_context_status"
]