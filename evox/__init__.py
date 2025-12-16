"""
Evox - Modern Python Microservices Framework

A lightweight, plugin-first microservices framework built on FastAPI with
hybrid orchestration, self-healing proxies, dynamic discovery, and intelligent caching.

Version 0.0.1-alpha - Early public alpha release
"""

__version__ = "0.0.2-alpha"

# Export core components
from .core import (
    service, get, post, put, delete, endpoint,
    Controller, GET, POST, PUT, DELETE, Intent, Param, Query, Body,
    proxy, data_io, data_intent, inject, override, reset_overrides, scheduler,
    PriorityLevel, get_priority_queue, initialize_queue,
    auth, AuthManager, AuthConfig, CIAClassification
)

__all__ = [
    "service", "get", "post", "put", "delete", "endpoint",
    "Controller", "GET", "POST", "PUT", "DELETE", "Intent", "Param", "Query", "Body",
    "proxy", "data_io", "data_intent", "inject", "override", "reset_overrides", "scheduler",
    "PriorityLevel", "get_priority_queue", "initialize_queue",
    "auth", "AuthManager", "AuthConfig", "CIAClassification"
]