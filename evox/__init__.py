"""
Evox - Modern Python Microservices Framework

A lightweight, plugin-first microservices framework built on FastAPI with
hybrid orchestration, self-healing proxies, dynamic discovery, and intelligent caching.

Version 0.1.2-beta - Public beta release
"""

__version__ = "0.1.2-beta"

# Export core components
from .core import (
    service, Service, get, post, put, delete, patch, head, options, endpoint,
    Controller, GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, Intent, Param, Query, Body,
    proxy, data_io, data_intent, inject, inject_from_annotation, override, reset_overrides, scheduler,
    PriorityLevel, get_priority_queue, initialize_queue,
    auth, AuthManager, AuthConfig, CIAClassification,
    inject_with_health_check, get_health_registry, get_service_health,
    BaseProvider, SQLiteStorageProvider, MemoryStorageProvider,
    Intent, IntentRegistry, get_intent_registry, extract_intents, get_field_intent, model_intent_score,
    analyze_schema_intent,
    DataIO, get_data_io, CircuitBreaker, EmergencySafetyBuffer, BackgroundSyncManager
)

__all__ = [
    "service", "Service", "get", "post", "put", "delete", "patch", "head", "options", "endpoint",
    "Controller", "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "Intent", "Param", "Query", "Body",
    "proxy", "data_io", "data_intent", "inject", "inject_from_annotation", "override", "reset_overrides", "scheduler",
    "PriorityLevel", "get_priority_queue", "initialize_queue",
    "auth", "AuthManager", "AuthConfig", "CIAClassification",
    "inject_with_health_check", "get_health_registry", "get_service_health",
    "BaseProvider", "SQLiteStorageProvider", "MemoryStorageProvider",
    "Intent", "IntentRegistry", "get_intent_registry", "extract_intents", "get_field_intent", "model_intent_score",
    "analyze_schema_intent",
    "DataIO", "get_data_io", "CircuitBreaker", "EmergencySafetyBuffer", "BackgroundSyncManager"
]