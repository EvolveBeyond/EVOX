"""
Background Task Management System for EVOX
Handles scheduled tasks, recurring jobs, and async processing.
"""

from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
from concurrent.futures import ThreadPoolExecutor
import functools
from ...data.intents.intent_system import Intent

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Status of a background task"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """Priority levels for tasks"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TaskInfo:
    """Information about a background task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Callable = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[Exception] = None
    retry_count: int = 0
    max_retries: int = 3

class TaskManager:
    """Background task management system"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running = False
        self._tasks: Dict[str, TaskInfo] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._worker_tasks: List[asyncio.Task] = []
        self._scheduled_tasks: Dict[str, asyncio.Task] = {}
        
        self.stats = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "active_tasks": 0
        }
    
    async def start(self):
        """Start the task manager"""
        if self._running:
            return
            
        self._running = True
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(worker_task)
        
        logger.info(f"Task manager started with {self.max_workers} workers")
    
    async def stop(self):
        """Stop the task manager"""
        if not self._running:
            return
            
        self._running = False
        
        # Cancel all scheduled tasks
        for task in self._scheduled_tasks.values():
            task.cancel()
        
        # Cancel worker tasks
        for worker_task in self._worker_tasks:
            worker_task.cancel()
        
        # Wait for tasks to complete
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        logger.info("Task manager stopped")
    
    def submit_task(
        self,
        func: Callable,
        *args,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        intent: Intent = Intent.STANDARD,
        **kwargs
    ) -> str:
        """Submit a task for background execution"""
        # If intent is provided, map it to priority
        if intent != Intent.STANDARD:
            intent_config = intent.get_config(intent)
            priority_mapping = {
                "low": TaskPriority.LOW,
                "normal": TaskPriority.NORMAL,
                "high": TaskPriority.HIGH
            }
            priority = priority_mapping.get(intent_config.task_priority, priority)
        
        task_info = TaskInfo(
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )
        
        self._tasks[task_info.id] = task_info
        # Priority queue uses negative values for higher priority
        priority_value = -task_info.priority.value
        self._task_queue.put_nowait((priority_value, task_info))
        
        self.stats["tasks_created"] += 1
        logger.info(f"Task submitted: {task_info.name} ({task_info.id}), intent: {intent}")
        
        return task_info.id
    
    async def schedule_task(
        self,
        func: Callable,
        delay: Union[float, timedelta],
        *args,
        name: Optional[str] = None,
        **kwargs
    ) -> str:
        """Schedule a task to run after a delay"""
        if isinstance(delay, timedelta):
            delay_seconds = delay.total_seconds()
        else:
            delay_seconds = float(delay)
        
        task_id = str(uuid.uuid4())
        
        async def delayed_task():
            await asyncio.sleep(delay_seconds)
            self.submit_task(func, *args, name=name, **kwargs)
        
        scheduled_task = asyncio.create_task(delayed_task())
        self._scheduled_tasks[task_id] = scheduled_task
        
        logger.info(f"Task scheduled: {name or func.__name__} in {delay_seconds}s")
        return task_id
    
    async def schedule_recurring_task(
        self,
        func: Callable,
        interval: Union[float, timedelta],
        *args,
        name: Optional[str] = None,
        **kwargs
    ) -> str:
        """Schedule a recurring task"""
        if isinstance(interval, timedelta):
            interval_seconds = interval.total_seconds()
        else:
            interval_seconds = float(interval)
        
        task_id = str(uuid.uuid4())
        
        async def recurring_task():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    if not self._running:
                        break
                    self.submit_task(func, *args, name=name, **kwargs)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in recurring task {name}: {e}")
        
        scheduled_task = asyncio.create_task(recurring_task())
        self._scheduled_tasks[task_id] = scheduled_task
        
        logger.info(f"Recurring task scheduled: {name or func.__name__} every {interval_seconds}s")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id in self._tasks:
            task_info = self._tasks[task_id]
            if task_info.status == TaskStatus.PENDING:
                task_info.status = TaskStatus.CANCELLED
                task_info.completed_at = datetime.now()
                self.stats["tasks_cancelled"] += 1
                logger.info(f"Task cancelled: {task_info.name}")
                return True
        
        # Try to cancel scheduled task
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id].cancel()
            del self._scheduled_tasks[task_id]
            return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskInfo]:
        """Get all tasks"""
        return list(self._tasks.values())
    
    async def _worker_loop(self, worker_name: str):
        """Worker loop that processes tasks"""
        logger.info(f"Worker {worker_name} started")
        
        while self._running:
            try:
                # Get task from queue
                priority, task_info = await self._task_queue.get()
                
                if not self._running:
                    break
                
                await self._execute_task(task_info)
                self._task_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker {worker_name}: {e}")
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _execute_task(self, task_info: TaskInfo):
        """Execute a task"""
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.now()
        self.stats["active_tasks"] += 1
        
        try:
            # Execute in thread pool for CPU-bound tasks
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                functools.partial(task_info.func, *task_info.args, **task_info.kwargs)
            )
            
            task_info.result = result
            task_info.status = TaskStatus.COMPLETED
            self.stats["tasks_completed"] += 1
            
        except Exception as e:
            task_info.error = e
            task_info.status = TaskStatus.FAILED
            self.stats["tasks_failed"] += 1
            logger.error(f"Task failed: {task_info.name} - {e}")
            
            # Handle retries
            if task_info.retry_count < task_info.max_retries:
                task_info.retry_count += 1
                logger.info(f"Retrying task {task_info.name} (attempt {task_info.retry_count})")
                # Re-queue with lower priority
                priority_value = -(task_info.priority.value - 1)  # Lower priority
                await self._task_queue.put((priority_value, task_info))
                return
        
        finally:
            task_info.completed_at = datetime.now()
            self.stats["active_tasks"] -= 1

# Global task manager instance
task_manager = TaskManager()

# Convenience functions
def run_in_background(
    func: Callable,
    *args,
    priority: TaskPriority = TaskPriority.NORMAL,
    intent: Intent = Intent.STANDARD,
    **kwargs
) -> str:
    """Run function in background"""
    return task_manager.submit_task(func, *args, priority=priority, intent=intent, **kwargs)

async def schedule_delayed(
    func: Callable,
    delay: Union[float, timedelta],
    *args,
    **kwargs
) -> str:
    """Schedule function to run after delay"""
    return await task_manager.schedule_task(func, delay, *args, **kwargs)

async def schedule_recurring(
    func: Callable,
    interval: Union[float, timedelta],
    *args,
    **kwargs
) -> str:
    """Schedule recurring function"""
    return await task_manager.schedule_recurring_task(func, interval, *args, **kwargs)

# Additional functions for compatibility

def get_task_manager():
    """Get the global task manager instance"""
    return task_manager

def submit_background_task(
    func: Callable,
    *args,
    priority: TaskPriority = TaskPriority.NORMAL,
    intent: Intent = Intent.STANDARD,
    **kwargs
) -> str:
    """Submit a background task"""
    return task_manager.submit_task(func, *args, priority=priority, intent=intent, **kwargs)

async def schedule_task(
    func: Callable,
    delay: Union[float, timedelta],
    *args,
    **kwargs
) -> str:
    """Schedule a task to run after delay"""
    return await task_manager.schedule_task(func, delay, *args, **kwargs)

def background_task(interval: int = 0):
    """Decorator for background tasks"""
    def decorator(func):
        if interval > 0:
            # Schedule as recurring task
            asyncio.run(task_manager.schedule_recurring_task(func, interval, func.__name__))
        else:
            # Just register for manual execution
            pass
        return func
    return decorator

def scheduled_task(interval: int):
    """Decorator for scheduled tasks"""
    def decorator(func):
        # Schedule the function to run at the specified interval
        asyncio.run(task_manager.schedule_recurring_task(func, timedelta(seconds=interval), func.__name__))
        return func
    return decorator

# Global scheduler instance for backward compatibility
scheduler = task_manager  # Using the default task manager instance

# Export public API
__all__ = [
    "TaskManager",
    "TaskInfo",
    "TaskStatus",
    "TaskPriority",
    "task_manager",
    "run_in_background",
    "schedule_delayed",
    "schedule_recurring",
    "get_task_manager",
    "submit_background_task",
    "schedule_task",
    "background_task",
    "scheduled_task"
]