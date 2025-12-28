"""
Shared Models for Enterprise System
==================================

These models are shared across multiple services in the enterprise system.
They demonstrate intent-aware design where different data types get
different treatment based on their declared intents.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from evox.core.intents import Intent as DataIntent


class BaseEntity(BaseModel):
    """
    Base entity with common fields for all enterprise entities.
    
    This base model includes common fields that all enterprise entities need,
    with appropriate data intents applied to sensitive information.
    """
    id: str
    created_at: str
    updated_at: str
    version: int = 1


class User(BaseEntity):
    """
    Enterprise User Model with Intent-Aware Fields
    
    This model demonstrates how different fields get different treatment
    based on their declared intents in an enterprise environment.
    """
    # Critical business data with strong consistency requirements
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="Critical user identifier requiring strong consistency"
    )
    
    # Sensitive data requiring encryption and privacy protection
    email: str = Field(
        ..., 
        pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$',
        description="Sensitive email requiring encryption and privacy protection"
    )
    
    # Business data with standard caching
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    
    # Optional demographic data
    age: int | None = Field(None, ge=0, le=150)
    department: str | None = None
    role: str = Field(default="user", description="User role in the system")
    
    # Compliance and audit fields
    is_active: bool = True
    last_login: str | None = None


class AuditLog(BaseEntity):
    """
    Audit Log Model for Enterprise Compliance
    
    This model demonstrates compliance-aware data handling where all
    operations must be logged and traceable for enterprise requirements.
    """
    user_id: str
    action: str
    resource: str
    timestamp: str
    ip_address: str | None = None
    user_agent: str | None = None
    success: bool = True
    details: Dict[str, Any] | None = None


class ServiceHealth(BaseModel):
    """
    Service Health Model for Enterprise Monitoring
    
    This model represents health information for services in the enterprise system.
    It demonstrates how health data gets different treatment in enterprise environments.
    """
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    timestamp: str
    response_time: float
    error_rate: float
    load: float
    details: Dict[str, Any] | None = None


class ServiceCommunicationRequest(BaseModel):
    """
    Service-to-Service Communication Request Model
    
    This model demonstrates how services communicate with each other
    in the enterprise system with appropriate authentication and authorization.
    """
    target_service: str
    operation: str
    payload: Dict[str, Any]
    priority: str = "normal"  # "low", "normal", "high", "critical"
    timeout: int = 30
    authentication_token: str | None = None
    caller_service: str | None = None