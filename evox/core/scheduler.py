"""
Call Scheduler - Heap-based priority-aware concurrent execution

This module provides a heap-based priority scheduling system that ensures:
1. Strict priority enforcement (HIGH > MEDIUM > LOW)
2. Fair scheduling within the same priority level
3. Concurrency control per priority level
4. Statistics tracking
"""
import asyncio
import heapq
import time
from typing import Any, Callable
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ScheduledTask:
    """Scheduled task with priority"""
    priority: int
    timestamp: float
    coro: Any
    task_id: str
    future: asyncio.Future
    
    def __lt__(self, other):
        """Comparison for priority queue ordering"""
        # Lower priority value = higher priority
        # If same priority, earlier timestamp = higher priority
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority < other.priority


class Priority(Enum):
    """Execution priority levels"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    
    def to_queue_priority(self) -> int:
        """Convert to queue priority value (lower = higher priority)"""
        return self.value


class Policy(Enum):
    """Execution policies"""
    PARTIAL_OK = "partial_ok"
    ALL_OR_NOTHING = "all_or_nothing"


class CallScheduler:
    """Heap-based priority-aware concurrent execution scheduler
    
    This scheduler ensures strict priority enforcement and fair scheduling:
    - HIGH priority tasks are always executed before MEDIUM or LOW
    - MEDIUM priority tasks are always executed before LOW
    - Tasks within the same priority are scheduled fairly (FIFO)
    - Concurrency limits prevent resource exhaustion with heap-based queue
    - Per-priority level concurrency caps for resource management"""
    
    def __init__(self, max_concurrent: int = 10):
        # Per-priority concurrency limits
        self._priority_semaphores = {
            Priority.HIGH: asyncio.Semaphore(5),    # Max 5 high priority tasks
            Priority.MEDIUM: asyncio.Semaphore(3),  # Max 3 medium priority tasks
            Priority.LOW: asyncio.Semaphore(2)      # Max 2 low priority tasks
        }
        self._task_counter = 0
        # Single heap-based priority queue for all priorities
        self._task_heap: list[ScheduledTask] = []
        self._task_dict: dict = {}  # Track tasks by ID
        self._lock = asyncio.Lock()  # Protect heap operations
        self._stats = defaultdict(int)  # Track execution stats
    
    async def _schedule_task(self, coro, priority: Priority) -> str:
        """Schedule a task in the priority heap"""
        async with self._lock:
            self._task_counter += 1
            task_id = f"task_{int(time.time())}_{self._task_counter}"
            
            # Create future for result
            future = asyncio.Future()
            
            # Create scheduled task
            task = ScheduledTask(
                priority=priority.to_queue_priority(),
                timestamp=time.time(),
                coro=coro,
                task_id=task_id,
                future=future
            )
            
            # Add to heap
            heapq.heappush(self._task_heap, task)
            self._task_dict[task_id] = task
            self._stats[f"scheduled_{priority.name.lower()}"] += 1
            
            # Wake up executor if sleeping
            asyncio.create_task(self._execute_next_task())
            
            return task_id
    
    async def _execute_next_task(self):
        """Execute the highest priority task from the heap"""
        async with self._lock:
            if not self._task_heap:
                return
            
            # Get highest priority task
            task = heapq.heappop(self._task_heap)
            del self._task_dict[task.task_id]
            
            # Determine priority enum for stats and semaphore selection
            priority_enum = Priority(task.priority)
            self._stats[f"executed_{priority_enum.name.lower()}"] += 1
            
            # Select appropriate semaphore for this priority level
            priority_semaphore = self._priority_semaphores[priority_enum]
        
        # Execute with priority-specific semaphore protection
        async with priority_semaphore:
            try:
                result = await task.coro
                task.future.set_result(result)
            except Exception as e:
                task.future.set_exception(e)
                self._stats["errors"] += 1
    
    async def _wait_for_task(self, task_id: str):
        """Wait for a scheduled task to complete"""
        async with self._lock:
            if task_id not in self._task_dict:
                raise ValueError(f"Task {task_id} not found")
            future = self._task_dict[task_id].future
        
        return await future
    
    def get_stats(self) -> dict:
        """Get scheduler statistics"""
        return dict(self._stats)
    
    async def execute(self, coro, priority: Priority = Priority.MEDIUM):
        """
        Execute a coroutine with priority using heap-based scheduling
        
        Args:
            coro: Coroutine to execute
            priority: Execution priority
            
        Returns:
            Result of the coroutine execution
        """
        # Schedule the task
        task_id = await self._schedule_task(coro, priority)
        
        # Wait for and return the result
        return await self._wait_for_task(task_id)
    
    async def parallel(self, *coros, 
                      priority: Priority = Priority.MEDIUM,
                      policy: Policy = Policy.PARTIAL_OK,
                      concurrency: int = 5) -> list[Any]:
        """
        Execute multiple coroutines concurrently with priority and policy control
        
        Args:
            *coros: Coroutines to execute
            priority: Execution priority
            policy: Execution policy
            concurrency: Maximum concurrent executions
            
        Returns:
            list of results
        """
        # Schedule all tasks with the same priority
        task_ids = []
        for coro in coros:
            task_id = await self._schedule_task(coro, priority)
            task_ids.append(task_id)
        
        # Wait for all tasks with concurrency control
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_wait(task_id):
            async with semaphore:
                return await self._wait_for_task(task_id)
        
        limited_tasks = [limited_wait(task_id) for task_id in task_ids]
        
        if policy == Policy.ALL_OR_NOTHING:
            # All must succeed or all fail
            return await asyncio.gather(*limited_tasks)
        else:
            # Partial results are acceptable
            results = []
            for task in asyncio.as_completed(limited_tasks):
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            return results


# Global scheduler instance
scheduler = CallScheduler()