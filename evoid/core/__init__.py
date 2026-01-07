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

from .application.service_builder import service, Service, get, post, put, delete, patch, head, options, endpoint, Controller, GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, Intent, Param, Query, Body
from .communication.proxy import proxy
from .data.data_io import data_io
from .data.intents.intent_system import Intent as data_intent
from .infrastructure.dependency_injection.injector import inject, override, reset_overrides, inject_from_annotation, inject_with_health_check, get_health_registry, get_service_health
from .infrastructure.scheduler.task_scheduler import scheduler
from .infrastructure.queue.priority_queue import PriorityLevel, get_priority_queue, initialize_queue
from .infrastructure.auth.auth_manager import auth, AuthManager, AuthConfig, CIAClassification
from .monitoring.intelligence.environmental_intelligence import EnvironmentalIntelligence, get_environmental_intelligence, auto_adjust_concurrency, understand_data_importance, understand_requester_context, get_current_context_status, SystemStatus
from .data.storage.providers.base_provider import BaseProvider
from .data.storage.registry import SQLiteStorageProvider, MemoryStorageProvider, ServiceRegistry, service_registry, initialize_service_registry
from .data.intents.intent_system import Intent, IntentRegistry, get_intent_registry, extract_intents, get_field_intent, model_intent_score
from .monitoring.intelligence.environmental_intelligence import analyze_schema_intent
from .data.data_io import DataIO, get_data_io, CircuitBreaker, EmergencySafetyBuffer, BackgroundSyncManager
from .utilities.serialization.fury_codec import fury_codec, serialize_object, deserialize_object
from .mapping.model_mapper import model_mapper, map_models, register_mapper, get_mapper, map_api_to_core, map_core_to_api
from .communication.message_bus import message_bus, get_event_bus, publish_message, subscribe_to_messages, on_message
from .infrastructure.scheduler.task_scheduler import task_manager, get_task_manager, run_in_background, submit_background_task, schedule_delayed, schedule_recurring, schedule_task, background_task, scheduled_task
from .utilities.caching.cache_layer import cache_layer, get_cache, cache_get, cache_set, cache_delete, cached
from .monitoring.metrics.performance_tracker import performance_bench, get_benchmark, run_benchmark, generate_benchmark_report, benchmark_serialization, benchmark_latency, benchmark_throughput

# New modules added
from .errors.BaseError import BaseError, ValidationError, StorageError, IntentError, CommunicationError, ConfigurationError, LifecycleError
from .mapping.model_mapper import model_mapper as core_model_mapper, map_api_to_core, map_core_to_api, register_mapper as core_register_mapper, get_mapper as core_get_mapper
from .utilities.serialization.fury_codec import fury_codec as serializer, serialize_object as core_serialize_object, deserialize_object as core_deserialize_object
from .communication.messaging.message_bus import event_bus, publish_event, subscribe_to_events, get_event_bus as get_internal_event_bus, on_event
from .data.persistence.intent_router import IntentRouter, PersistenceGateway, DatabaseServiceManager, persistence_gateway
from .data.persistence.intent_router import save_model, get_model, delete_model, query_models

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
    "ServiceRegistry",
    "service_registry",
    "initialize_service_registry",
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
    "start_data_io_background_sync",
    "fury_codec",
    "serialize_object",
    "deserialize_object",
    "model_mapper",
    "map_models",
    "register_mapper",
    "get_mapper",
    "map_api_to_core",
    "map_core_to_api",
    "message_bus",
    "get_event_bus",
    "publish_message",
    "subscribe_to_messages",
    "on_message",
    "task_manager",
    "get_task_manager",
    "run_in_background",
    "submit_background_task",
    "schedule_task",
    "background_task",
    "scheduled_task",
    "get_cache",
    "cache_layer",
    "cache_get",
    "cache_set",
    "cache_delete",
    "cached",
    "performance_bench",
    "get_benchmark",
    "run_benchmark",
    "generate_benchmark_report",
    "benchmark_serialization",
    "benchmark_latency",
    "benchmark_throughput",
    
    # New modules
    "BaseError",
    "ValidationError",
    "StorageError",
    "IntentError",
    "CommunicationError",
    "ConfigurationError",
    "LifecycleError",
    "core_model_mapper",
    "map_api_to_core",
    "map_core_to_api",
    "core_register_mapper",
    "core_get_mapper",
    "serializer",
    "core_serialize_object",
    "core_deserialize_object",

    "event_bus",
    "publish_event",
    "subscribe_to_events",
    "get_internal_event_bus",
    "on_event",
    # Persistence components
    "IntentRouter",
    "PersistenceGateway",
    "DatabaseServiceManager",
    "persistence_gateway",
    "save_model",
    "get_model",
    "delete_model",
    "query_models"
]