"""
Evox Core Framework Components

This module exports all core components of the Evox framework including:
- Service builder for creating services
- Proxy for service-to-service communication
- Data IO for intent-aware data operations
- Dependency injection utilities
- Scheduler for background tasks
- Priority queue for request management
"""

from .service_builder import service, get, post, put, delete, patch, head, options, endpoint, Controller, GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, Intent, Param, Query, Body
from .proxy import proxy
from .storage import data_io, data_intent
from .inject import inject, override, reset_overrides, inject_dependency
from .scheduler import scheduler
from .queue import PriorityLevel, get_priority_queue, initialize_queue
from .auth import auth, AuthManager, AuthConfig, CIAClassification
from .intelligence import EnvironmentalIntelligence, get_environmental_intelligence, auto_adjust_concurrency, understand_data_importance, understand_requester_context

__all__ = [
    "service", 
    "get", 
    "post", 
    "put", 
    "delete", 
    "patch",
    "head",
    "options",
    "endpoint", 
    "Controller",
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "HEAD",
    "OPTIONS",
    "Intent",
    "Param",
    "Query",
    "Body",
    "proxy", 
    "data_io", 
    "data_intent", 
    "inject", 
    "inject_dependency",
    "override",
    "reset_overrides",
    "scheduler",
    "PriorityLevel",
    "get_priority_queue",
    "initialize_queue",
    "auth",
    "AuthManager",
    "AuthConfig",
    "CIAClassification",
    "EnvironmentalIntelligence",
    "get_environmental_intelligence",
    "auto_adjust_concurrency",
    "understand_data_importance",
    "understand_requester_context"
]