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
    id: str = Field(
        ..., 
        description="Unique identifier for the entity",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    created_at: str = Field(
        ..., 
        description="Entity creation timestamp",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    updated_at: str = Field(
        ..., 
        description="Entity last update timestamp",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    version: int = Field(
        default=1, 
        description="Entity version for optimistic locking",
        json_schema_extra={"intent": DataIntent.LAZY}
    )


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
        description="Critical user identifier requiring strong consistency",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    
    # Sensitive data requiring encryption and privacy protection
    email: str = Field(
        ..., 
        pattern=r'^[\w\.-]+@[\w\.-]+\.+\w+$',
        description="Sensitive email requiring encryption and privacy protection",
        json_schema_extra={"intent": DataIntent.SENSITIVE}
    )
    
    # Business data with standard caching
    first_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    last_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    
    # Optional demographic data
    age: int | None = Field(
        None, 
        ge=0, 
        le=150,
        json_schema_extra={"intent": DataIntent.EPHEMERAL}
    )
    department: str | None = Field(
        None,
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    role: str = Field(
        default="user", 
        description="User role in the system",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    
    # Compliance and audit fields
    is_active: bool = Field(
        default=True,
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    last_login: str | None = Field(
        None,
        json_schema_extra={"intent": DataIntent.LAZY}
    )


class AuditLog(BaseEntity):
    """
    Audit Log Model for Enterprise Compliance
    
    This model demonstrates compliance-aware data handling where all
    operations must be logged and traceable for enterprise requirements.
    """
    user_id: str = Field(
        ..., 
        description="ID of the user performing the action",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    action: str = Field(
        ..., 
        description="Action performed by the user",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    resource: str = Field(
        ..., 
        description="Resource that was accessed",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    timestamp: str = Field(
        ..., 
        description="Time when the action occurred",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    ip_address: str | None = Field(
        None,
        description="IP address of the user",
        json_schema_extra={"intent": DataIntent.SENSITIVE}
    )
    user_agent: str | None = Field(
        None,
        description="User agent string of the client",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    success: bool = Field(
        default=True,
        description="Whether the action was successful",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    details: Dict[str, Any] | None = Field(
        None,
        description="Additional details about the action",
        json_schema_extra={"intent": DataIntent.LAZY}
    )


class ServiceHealth(BaseModel):
    """
    Service Health Model for Enterprise Monitoring
    
    This model represents health information for services in the enterprise system.
    It demonstrates how health data gets different treatment in enterprise environments.
    """
    service_name: str = Field(
        ..., 
        description="Name of the service",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    status: str = Field(
        ..., 
        description="Health status of the service (healthy/degraded/unhealthy/unknown)",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    timestamp: str = Field(
        ..., 
        description="Time when health was checked",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    response_time: float = Field(
        ..., 
        description="Response time in milliseconds",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    error_rate: float = Field(
        ..., 
        description="Current error rate",
        json_schema_extra={"intent": DataIntent.CRITICAL}
    )
    load: float = Field(
        ..., 
        description="Current system load",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    details: Dict[str, Any] | None = Field(
        None,
        description="Additional health details",
        json_schema_extra={"intent": DataIntent.LAZY}
    )


class ServiceCommunicationRequest(BaseModel):
    """
    Service-to-Service Communication Request Model
    
    This model demonstrates how services communicate with each other
    in the enterprise system with appropriate authentication and authorization.
    """
    target_service: str = Field(
        ..., 
        description="Name of the target service",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    operation: str = Field(
        ..., 
        description="Operation to perform on the target service",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    payload: Dict[str, Any] = Field(
        ..., 
        description="Data to send to the target service",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    priority: str = Field(
        default="normal", 
        description="Priority of the request (low/normal/high/critical)",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        json_schema_extra={"intent": DataIntent.LAZY}
    )
    authentication_token: str | None = Field(
        None,
        description="Authentication token for service-to-service communication",
        json_schema_extra={"intent": DataIntent.SENSITIVE}
    )
    caller_service: str | None = Field(
        None,
        description="Name of the calling service",
        json_schema_extra={"intent": DataIntent.LAZY}
    )