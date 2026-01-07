"""
Shared Core Models for EVOX
Common data models used across the core system.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

class MessagePriority(Enum):
    """Priority levels for messages"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class ProcessingStatus(Enum):
    """Status of processing operations"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class CoreMessage:
    """Core message structure used internally"""
    id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: Optional[str] = None
    message_type: str = ""
    payload: Any = None
    priority: MessagePriority = MessagePriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if message has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

@dataclass
class CoreResponse:
    """Standard response structure"""
    success: bool = True
    message: str = ""
    data: Any = None
    error_code: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: Optional[str] = None

@dataclass
class ProcessingResult:
    """Result of a processing operation"""
    status: ProcessingStatus
    result_data: Any = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None  # in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceHealth:
    """Service health status information"""
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    uptime: float  # in seconds
    last_check: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

@dataclass
class SystemMetrics:
    """System-wide metrics"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_io: Dict[str, float] = field(default_factory=dict)
    active_connections: int = 0
    request_rate: float = 0.0
    error_rate: float = 0.0

@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0
    tier_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

@dataclass
class TaskStats:
    """Background task statistics"""
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_processing_time: float = 0.0
    queue_size: int = 0

# Utility functions
def create_success_response(data: Any = None, message: str = "Success") -> CoreResponse:
    """Create a successful response"""
    return CoreResponse(success=True, message=message, data=data)

def create_error_response(error_message: str, error_code: Optional[str] = None) -> CoreResponse:
    """Create an error response"""
    return CoreResponse(
        success=False,
        message=error_message,
        error_code=error_code
    )

def calculate_hit_rate(hits: int, misses: int) -> float:
    """Calculate cache hit rate"""
    total = hits + misses
    return hits / total if total > 0 else 0.0

def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

# Export public API
__all__ = [
    "CoreMessage",
    "CoreResponse",
    "ProcessingResult",
    "ServiceHealth",
    "SystemMetrics",
    "CacheStats",
    "TaskStats",
    "MessagePriority",
    "ProcessingStatus",
    "create_success_response",
    "create_error_response",
    "calculate_hit_rate",
    "format_bytes"
]