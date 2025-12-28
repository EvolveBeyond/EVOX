"""
Intent-Aware Priority Queue System - Registry-Driven, Context-Aware Request Processing

This module provides an Intent-Aware priority queue system that:
1. Processes requests based on priority levels
2. Adapts to system resource availability
3. Integrates with the intent system for intelligent request handling
4. Implements load shedding when system resources are constrained

Design Philosophy:
- Priority-based processing: Critical requests get processed first
- Adaptive behavior: Adjusts to system load conditions
- Intent-aware: Leverages intent metadata for smarter processing
- Resource-conscious: Implements load shedding when necessary
"""

import asyncio
import heapq
from enum import Enum
from typing import Any, Callable, Coroutine
from dataclasses import dataclass, field

import time
import logging
from .intents import Intent, get_intent_registry


class PriorityLevel(Enum):
    """
    Priority levels for request processing
    
    Rationale: Standardized priority levels ensure consistent request
    processing across the framework based on declared intent and importance.
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class QueueItem:
    """
    Represents an item in the priority queue
    
    Rationale: Encapsulates request data with priority and timing information
    to enable proper queue management and processing.
    """
    priority: PriorityLevel
    timestamp: float
    request_coro: Coroutine[Any, Any, Any]
    intent: Intent | None = None
    path: str | None = None
    method: str | None = None
    # Use field(default_factory=int) to avoid mutable default argument
    _queue_order: int = field(default_factory=lambda: int(time.time() * 1000000) % 1000000)  # Use timestamp-based unique ID
    
    def __lt__(self, other):
        """
        Compare queue items based on priority and timestamp
        
        Rationale: Ensures high-priority items are processed first,
        with timestamp as tie-breaker for same priority items.
        """
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value  # Higher value = higher priority
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp  # Earlier timestamp = higher priority
        return self._queue_order < other._queue_order  # Tie-breaker using unique ID


class PriorityQueue:
    """
    Priority queue system for managing request processing
    
    This system implements:
    - Priority-based request processing
    - Adaptive concurrency based on system load
    - Intent-aware request handling
    - Load shedding during high resource usage
    
    Design Rationale:
    - Centralized queue management for consistent request handling
    - Adaptive behavior based on system conditions
    - Integration with intent system for intelligent processing
    """
    
    def __init__(self, max_concurrent: int = 10):
        self._queue = []
        self._max_concurrent = max_concurrent
        self._current_tasks = 0
        self._lock = asyncio.Lock()
        self._shutdown = False
        self._cpu_threshold = 0.8  # 80% CPU usage
        self._memory_threshold = 0.8  # 80% memory usage
        self._default_high_priority_concurrency = 5
        self._default_medium_priority_concurrency = 3
        self._default_low_priority_concurrency = 1
    
    async def submit(self, 
                     request_coro: Coroutine[Any, Any, Any], 
                     priority: PriorityLevel = PriorityLevel.MEDIUM,
                     intent: Intent | None = None,
                     path: str | None = None,
                     method: str | None = None) -> Any:
        """
        Submit a request to the priority queue
        
        Args:
            request_coro: The coroutine to execute
            priority: Priority level for the request
            intent: Intent of the request for intelligent handling
            path: Path of the request (for intent lookup)
            method: HTTP method of the request (for intent lookup)
        
        Returns:
            Result of the coroutine execution
        """
        # Import intelligence here to avoid circular import
        from .intelligence import get_current_context_status, SystemStatus
        
        # Check system status and apply admission control
        system_status = get_current_context_status()
        
        # Apply intent-aware admission control
        if not self._is_request_allowed(system_status, intent, priority, path, method):
            # Log the load shedding event
            logging.warning(
                f"Load shedding: Request to {method} {path} with intent {intent} and priority {priority.name} "
                f"rejected due to system status {system_status}"
            )
            # Raise an exception that can be caught by middleware
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Service temporarily unavailable due to high load")
        
        # Create queue item
        item = QueueItem(
            priority=priority,
            timestamp=time.time(),
            request_coro=request_coro,
            intent=intent,
            path=path,
            method=method
        )
        
        # Add to queue
        async with self._lock:
            heapq.heappush(self._queue, item)
        
        # Process queue if not already processing
        asyncio.create_task(self._process_queue())
        
        # Wait for the result
        return await self._execute_request(item)
    
    def _is_request_allowed(self,
                           system_status,  # SystemStatus - import happens inside function
                           intent: Intent | None,
                           priority: PriorityLevel,
                           path: str | None,
                           method: str | None) -> bool:
        """
        Determine if a request should be allowed based on system status and intent.
        
        Rationale: Implements intent-aware admission control to prioritize critical
        requests during system stress while allowing less important requests to be shed.
        
        Args:
            system_status: Current system status
            intent: Intent of the request
            priority: Priority level of the request
            path: Path of the request
            method: HTTP method of the request
            
        Returns:
            True if request should be allowed, False otherwise
        """
        # Import SystemStatus here to avoid forward reference issue
        from .intelligence import SystemStatus
        
        # If system is healthy, allow everything
        if system_status == SystemStatus.GREEN:
            return True
        
        # If system is in critical state (RED)
        if system_status == SystemStatus.RED:
            # Only allow critical intents or high priority requests
            return (intent == Intent.CRITICAL or 
                    priority == PriorityLevel.HIGH or
                    (intent is None and priority == PriorityLevel.HIGH))
        
        # If system is under warning (YELLOW)
        if system_status == SystemStatus.YELLOW:
            # Allow everything except ephemeral or low priority requests
            return not (intent == Intent.EPHEMERAL or 
                       priority == PriorityLevel.LOW)
        
        # Default to allowing the request
        return True
    
    async def _execute_request(self, item: QueueItem) -> Any:
        """
        Execute a single request with proper resource management.
        
        Args:
            item: The queue item to execute
            
        Returns:
            Result of the request execution
        """
        try:
            # Execute the coroutine and return its result
            return await item.request_coro
        except Exception as e:
            # Log the error but don't re-raise to avoid breaking the queue
            logging.error(f"Error executing request in queue: {e}")
            raise
    
    async def _process_queue(self):
        """
        Process items in the queue based on priority and system resources.
        
        Rationale: Asynchronous queue processing ensures requests are handled
        efficiently while respecting system resource constraints.
        """
        while self._queue and not self._shutdown:
            async with self._lock:
                if not self._queue:
                    break
                
                # Get the highest priority item
                item = heapq.heappop(self._queue)
            
            # Execute the item
            try:
                # For now, we'll execute directly - in a real system we might want to 
                # implement more sophisticated concurrency controls based on priority
                await self._execute_request(item)
            except Exception:
                # If execution fails, continue to next item
                continue
    
    def adjust_concurrency_based_on_resources(self, cpu_usage: float, memory_usage: float):
        """
        Adjust queue concurrency based on system resource usage.
        
        Rationale: Adaptive concurrency helps maintain system stability
        by reducing concurrent operations when resources are constrained.
        
        Args:
            cpu_usage: Current CPU usage (0.0-1.0)
            memory_usage: Current memory usage (0.0-1.0)
        """
        # Calculate max concurrent based on resource usage
        max_usage = max(cpu_usage, memory_usage)
        
        if max_usage > 0.9:  # Very high usage
            self._max_concurrent = max(1, self._default_low_priority_concurrency)
        elif max_usage > 0.75:  # High usage
            self._max_concurrent = max(2, self._default_medium_priority_concurrency)
        else:  # Normal usage
            self._max_concurrent = self._default_high_priority_concurrency
    
    async def gather(self,
                     *requests,
                     priority: PriorityLevel = PriorityLevel.MEDIUM,
                     concurrency: int = 5) -> list[Any]:
        """
        Execute multiple requests concurrently with priority and concurrency control.
        
        This method integrates with the priority-aware queue system to execute
        multiple requests with controlled concurrency and priority levels.
        
        Args:
            *requests: Request coroutines to execute
            priority: Priority level for all requests
            concurrency: Maximum number of concurrent requests
            
        Returns:
            list of results in the same order as requests
        """
        # Limit concurrency using asyncio.Semaphore
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_request(request_coro):
            async with semaphore:
                # Import intelligence here to avoid circular import
                from .intelligence import get_current_context_status, SystemStatus
                from .intents import Intent, get_intent_registry
                
                # Check system status and apply admission control
                system_status = get_current_context_status()
                
                # Apply intent-aware admission control
                # For gather operations, we'll use the default priority
                if not self._is_request_allowed(system_status, None, priority, "gather", "INTERNAL"):
                    # Log the load shedding event
                    logging.warning(
                        f"Load shedding: Gather request with priority {priority.name} "
                        f"rejected due to system status {system_status}"
                    )
                    # Raise an exception that can be caught by middleware
                    from fastapi import HTTPException
                    raise HTTPException(status_code=503, detail="Service temporarily unavailable due to high load")
                
                return await self.submit(request_coro, priority=priority)
        
        # Execute all requests concurrently
        tasks = [limited_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for exceptions and raise them if needed
        for result in results:
            if isinstance(result, Exception):
                raise result
        
        return results


# Global priority queue instance
_priority_queue = PriorityQueue()


def get_priority_queue() -> PriorityQueue:
    """
    Get the global priority queue instance.
    
    Returns:
        PriorityQueue instance
    """
    return _priority_queue


def initialize_queue(max_concurrent: int = 10):
    """
    Initialize the priority queue with specified concurrency.
    
    Args:
        max_concurrent: Maximum number of concurrent operations
    """
    global _priority_queue
    _priority_queue = PriorityQueue(max_concurrent=max_concurrent)


__all__ = [
    "PriorityLevel", 
    "get_priority_queue", 
    "initialize_queue",
    "QueueItem"
]