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

from .service_builder import service, Service, get, post, put, delete, patch, head, options, endpoint, Controller, GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, Intent, Param, Query, Body
from .proxy import proxy
from .storage import data_io, data_intent
from .inject import inject, override, reset_overrides, inject_from_annotation, inject_with_health_check, get_health_registry, get_service_health
from .scheduler import scheduler
from .queue import PriorityLevel, get_priority_queue, initialize_queue
from .auth import auth, AuthManager, AuthConfig, CIAClassification
from .intelligence import EnvironmentalIntelligence, get_environmental_intelligence, auto_adjust_concurrency, understand_data_importance, understand_requester_context, get_current_context_status, SystemStatus
from .common import BaseProvider
from .storage_provider import SQLiteStorageProvider, MemoryStorageProvider
from .intents import Intent, IntentRegistry, get_intent_registry, extract_intents, get_field_intent, model_intent_score
from .intelligence import analyze_schema_intent
from .data_io import DataIO, get_data_io, CircuitBreaker, EmergencySafetyBuffer, BackgroundSyncManager

__all__ = [
    "service", 
    "Service",
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
    "inject_from_annotation",
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
    "understand_requester_context",
    "get_current_context_status",
    "SystemStatus",
    "BaseProvider",
    "SQLiteStorageProvider",
    "MemoryStorageProvider",
    "Intent",
    "IntentRegistry",
    "get_intent_registry",
    "extract_intents",
    "get_field_intent",
    "model_intent_score",
    "analyze_schema_intent",
    "DataIO",
    "get_data_io",
    "CircuitBreaker",
    "EmergencySafetyBuffer",
    "BackgroundSyncManager",
    "start_data_io_background_sync"
]