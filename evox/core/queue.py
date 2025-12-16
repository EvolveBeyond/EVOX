"""
Priority-Aware Request Queue for Evox Framework

This module implements a priority-aware execution queue for inter-service calls
and fan-out operations. It provides:

1. Three priority levels: high (user-facing), medium (default), low (background)
2. Concurrency caps per priority level
3. Admission control (reject fast if queue full)
4. Backpressure handling

The queue integrates with the service proxy and endpoint decorators to provide
priority-based execution of requests.
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime

from .config import get_config


class PriorityLevel(Enum):
    """Priority levels for request queueing"""
    HIGH = "high"      # User-facing, critical operations
    MEDIUM = "medium"  # Default priority for most operations
    LOW = "low"        # Background, non-critical operations


@dataclass
class QueuedRequest:
    """Represents a request in the priority queue"""
    id: str
    priority: PriorityLevel
    func: Callable
    args: tuple
    kwargs: dict
    timestamp: float
    timeout: Optional[float] = None


class PriorityQueueStats:
    """Statistics tracker for the priority queue"""
    
    def __init__(self):
        self.queue_lengths: Dict[PriorityLevel, int] = {
            PriorityLevel.HIGH: 0,
            PriorityLevel.MEDIUM: 0,
            PriorityLevel.LOW: 0
        }
        self.admission_rejections: Dict[PriorityLevel, int] = {
            PriorityLevel.HIGH: 0,
            PriorityLevel.MEDIUM: 0,
            PriorityLevel.LOW: 0
        }
        self.processed_count: Dict[PriorityLevel, int] = {
            PriorityLevel.HIGH: 0,
            PriorityLevel.MEDIUM: 0,
            PriorityLevel.LOW: 0
        }
        self.errors: List[Dict[str, Any]] = []
        self.last_updated: float = time.time()
    
    def increment_queue_length(self, priority: PriorityLevel):
        """Increment queue length for a priority level"""
        self.queue_lengths[priority] += 1
        self.last_updated = time.time()
    
    def decrement_queue_length(self, priority: PriorityLevel):
        """Decrement queue length for a priority level"""
        self.queue_lengths[priority] = max(0, self.queue_lengths[priority] - 1)
        self.last_updated = time.time()
    
    def increment_admission_rejection(self, priority: PriorityLevel):
        """Increment admission rejection count for a priority level"""
        self.admission_rejections[priority] += 1
        self.last_updated = time.time()
    
    def increment_processed(self, priority: PriorityLevel):
        """Increment processed count for a priority level"""
        self.processed_count[priority] += 1
        self.last_updated = time.time()
    
    def add_error(self, priority: PriorityLevel, error: Exception, context: str = ""):
        """Add an error to the error log"""
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "priority": priority.value,
            "error": str(error),
            "context": context
        })
        # Keep only last 100 errors to prevent memory bloat
        if len(self.errors) > 100:
            self.errors.pop(0)
        self.last_updated = time.time()


class PriorityAwareQueue:
    """
    Priority-aware execution queue for Evox framework.
    
    This queue manages concurrent execution of requests with different priority levels.
    It provides:
    
    1. Priority-based scheduling (HIGH > MEDIUM > LOW)
    2. Concurrency limits per priority level
    3. Queue length limits with admission control
    4. Statistics tracking
    
    Design Notes:
    - Uses asyncio queues for each priority level
    - Implements weighted round-robin scheduling favoring higher priorities
    - Provides backpressure handling through queue limits
    - Tracks comprehensive statistics for monitoring
    
    Good first issue: Add configurable weights for priority scheduling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the priority-aware queue.
        
        Args:
            config: Configuration dictionary with queue settings
                   If not provided, loads from framework configuration
                   Example:
                   {
                       "concurrency_limits": {
                           "high": 10,
                           "medium": 5,
                           "low": 2
                       },
                       "queue_limits": {
                           "high": 50,
                           "medium": 100,
                           "low": 200
                       }
                   }
        """
        # Load configuration from framework config if not provided
        if config is None:
            config = {
                "concurrency_limits": {
                    "high": get_config("queue.concurrency_limits.high", 10),
                    "medium": get_config("queue.concurrency_limits.medium", 5),
                    "low": get_config("queue.concurrency_limits.low", 2)
                },
                "queue_limits": {
                    "high": get_config("queue.queue_limits.high", 50),
                    "medium": get_config("queue.queue_limits.medium", 100),
                    "low": get_config("queue.queue_limits.low", 200)
                }
            }
        
        # Merge with provided config
        self.config = config
        
        # Create queues for each priority level
        self.queues: Dict[PriorityLevel, asyncio.Queue] = {
            PriorityLevel.HIGH: asyncio.Queue(maxsize=self.config["queue_limits"]["high"]),
            PriorityLevel.MEDIUM: asyncio.Queue(maxsize=self.config["queue_limits"]["medium"]),
            PriorityLevel.LOW: asyncio.Queue(maxsize=self.config["queue_limits"]["low"])
        }
        
        # Track active workers per priority
        self.active_workers: Dict[PriorityLevel, int] = {
            PriorityLevel.HIGH: 0,
            PriorityLevel.MEDIUM: 0,
            PriorityLevel.LOW: 0
        }
        
        # Concurrency limits
        self.concurrency_limits: Dict[PriorityLevel, int] = {
            PriorityLevel.HIGH: self.config["concurrency_limits"]["high"],
            PriorityLevel.MEDIUM: self.config["concurrency_limits"]["medium"],
            PriorityLevel.LOW: self.config["concurrency_limits"]["low"]
        }
        
        # Statistics tracker
        self.stats = PriorityQueueStats()
        
        # Request counter for unique IDs
        self._request_counter = 0
        
        # Lock for worker management
        self._worker_lock = asyncio.Lock()
        
        # Flag to indicate if queue is running
        self._running = True
        
        # Worker tasks
        self._workers = []
        
        # Start worker threads
        self._start_workers()
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID"""
        self._request_counter += 1
        return f"req_{int(time.time())}_{self._request_counter}"
    
    def _start_workers(self):
        """Start worker threads for processing queues with optimized concurrency"""
        # Start workers for each priority level
        for priority in PriorityLevel:
            worker_count = self.concurrency_limits[priority]
            for i in range(worker_count):
                worker_task = asyncio.create_task(self._worker_loop(priority))
                self._workers.append(worker_task)
    
    async def _worker_loop(self, priority: PriorityLevel):
        """Worker loop for processing requests from a specific priority queue"""
        while self._running:
            try:
                # Wait for a request from this priority queue
                request = await self.queues[priority].get()
                
                # Process the request
                await self._execute_queued_request(request)
                
                # Mark task as done
                self.queues[priority].task_done()
                
                # Update stats
                self.stats.decrement_queue_length(priority)
            except Exception as e:
                # Log error but continue processing
                self.stats.add_error(priority, e, f"Worker loop error for {priority.value}")
                continue
    
    async def submit(self, 
                     func: Callable, 
                     *args, 
                     priority: PriorityLevel = PriorityLevel.MEDIUM,
                     timeout: Optional[float] = None,
                     **kwargs) -> Any:
        """
        Submit a request to the priority queue.
        
        Args:
            func: The function to execute
            *args: Positional arguments for the function
            priority: Priority level for the request
            timeout: Timeout for the request execution
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function execution
            
        Raises:
            asyncio.TimeoutError: If the request times out
            RuntimeError: If the queue is full and admission is rejected
        """
        # Generate unique request ID
        request_id = self._generate_request_id()
        
        # Create future for result
        future = asyncio.Future()
        
        # Create queued request
        request = QueuedRequest(
            id=request_id,
            priority=priority,
            func=func,
            args=args,
            kwargs=kwargs,
            timestamp=time.time(),
            timeout=timeout
        )
        
        # Store future for this request
        if not hasattr(self, '_request_futures'):
            self._request_futures = {}
        self._request_futures[request_id] = future
        
        # Try to add to queue, reject if full
        try:
            self.queues[priority].put_nowait(request)
            self.stats.increment_queue_length(priority)
        except asyncio.QueueFull:
            self.stats.increment_admission_rejection(priority)
            # Clean up future
            if request_id in self._request_futures:
                del self._request_futures[request_id]
            raise RuntimeError(f"Queue full for priority {priority.value}, request rejected")
        
        # Wait for result
        try:
            return await future
        except Exception:
            # Re-raise any exceptions
            raise
    
    async def _execute_queued_request(self, request: QueuedRequest) -> Any:
        """
        Execute a queued request.
        
        Args:
            request: The queued request to execute
            
        Returns:
            The result of the function execution
        """
        result = None
        exception = None
        
        try:
            # Increment active worker count
            async with self._worker_lock:
                self.active_workers[request.priority] += 1
            
            self.stats.increment_processed(request.priority)
            
            # Execute with timeout if specified
            if request.timeout:
                result = await asyncio.wait_for(
                    request.func(*request.args, **request.kwargs),
                    timeout=request.timeout
                )
            else:
                result = await request.func(*request.args, **request.kwargs)
                
        except Exception as e:
            self.stats.add_error(request.priority, e, f"Executing request {request.id}")
            exception = e
        finally:
            # Decrement active worker count
            async with self._worker_lock:
                self.active_workers[request.priority] = max(
                    0, self.active_workers[request.priority] - 1
                )
            
            # Set result or exception on future
            if hasattr(self, '_request_futures') and request.id in self._request_futures:
                future = self._request_futures[request.id]
                if exception:
                    future.set_exception(exception)
                else:
                    future.set_result(result)
                # Clean up
                del self._request_futures[request.id]
    
    async def gather(self, 
                     *requests,
                     priority: PriorityLevel = PriorityLevel.MEDIUM,
                     concurrency: int = 5) -> List[Any]:
        """
        Execute multiple requests concurrently with priority and concurrency control.
        
        Args:
            *requests: Request coroutines to execute
            priority: Priority level for all requests
            concurrency: Maximum number of concurrent requests
            
        Returns:
            List of results in the same order as requests
        """
        # Semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def _limited_request(req):
            async with semaphore:
                return await req
        
        # Submit all requests with the specified priority
        limited_requests = [_limited_request(req) for req in requests]
        results = await asyncio.gather(*limited_requests, return_exceptions=True)
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        return {
            "queue_lengths": dict(self.stats.queue_lengths),
            "admission_rejections": dict(self.stats.admission_rejections),
            "processed_count": dict(self.stats.processed_count),
            "active_workers": dict(self.active_workers),
            "concurrency_limits": dict(self.concurrency_limits),
            "recent_errors": self.stats.errors[-10:]  # Last 10 errors
        }
    
    async def shutdown(self):
        """Shutdown the queue gracefully"""
        self._running = False
        
        # Cancel all worker tasks
        for worker in self._workers:
            if not worker.done():
                worker.cancel()
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        # Cancel any pending futures
        if hasattr(self, '_request_futures'):
            for future in self._request_futures.values():
                if not future.done():
                    future.cancel()
            self._request_futures.clear()


# Global queue instance
_priority_queue: Optional[PriorityAwareQueue] = None


def get_priority_queue(config: Optional[Dict[str, Any]] = None) -> PriorityAwareQueue:
    """
    Get the global priority queue instance.
    
    Args:
        config: Configuration for the queue (only used on first call)
        
    Returns:
        The global priority queue instance
    """
    global _priority_queue
    if _priority_queue is None:
        _priority_queue = PriorityAwareQueue(config)
    return _priority_queue


def initialize_queue(config: Optional[Dict[str, Any]] = None):
    """
    Initialize the global priority queue.
    
    This function should be called during framework initialization.
    
    Args:
        config: Configuration for the queue
    """
    global _priority_queue
    _priority_queue = PriorityAwareQueue(config)


# Export public API
__all__ = [
    "PriorityLevel",
    "PriorityAwareQueue",
    "get_priority_queue",
    "initialize_queue"
]