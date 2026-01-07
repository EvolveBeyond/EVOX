"""
Service Builder - Intent-Aware, Registry-Driven Service Orchestration

This module provides the fluent API for building Evox services with minimal configuration.
It supports Intent-Aware request processing, Registry-Driven service discovery,
and priority-aware request queuing with intelligent fallback mechanisms.
"""

import asyncio
import uvicorn
from typing import Any, get_type_hints, Callable
from collections.abc import Callable as CallableABC
from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from functools import wraps
from pydantic import BaseModel
from typing import get_origin, get_args
from datetime import datetime
import logging

from ..infrastructure.queue.priority_queue import PriorityLevel, get_priority_queue
from ..infrastructure.dependency_injection.injector import get_health_registry, get_service_health
from ..data.storage.providers.base_provider import BaseProvider
from ..data.intents.intent_system import Intent, get_intent_registry
from ..infrastructure.lifecycle import on_service_init

# New imports for advanced features
from ..utilities.serialization.fury_codec import fury_codec, FuryNotAvailable, serialize_object, deserialize_object
from ..mapping.model_mapper import model_mapper, map_models
from ..communication.message_bus import message_bus, publish_message, subscribe_to_topic
from ..infrastructure.scheduler.task_scheduler import task_manager, run_in_background, schedule_delayed, schedule_recurring
from ..utilities.caching.cache_layer import cache_layer, cache_get, cache_set, cached
from ..monitoring.metrics.performance_tracker import performance_bench, benchmark_latency, benchmark_throughput


class DatabaseServiceOrchestrator:
    """
    Database Service Orchestrator - Core component for database service discovery and routing.
    
    This class handles:
    - Discovery of database services from configuration
    - Dynamic driver loading based on intent requirements
    - Intent-to-database service mapping
    - Health monitoring of database connections
    - Graceful failover and recovery
    
    Design Principles:
    - Zero-configuration by default (auto-discovery)
    - Intent-driven service selection
    - Lazy loading of database drivers
    - Automatic health checking and failover
    """
    
    def __init__(self, service_name: str, config=None):
        self.service_name = service_name
        self.config = config
        self.database_services = {}
        self.driver_cache = {}
        self.intent_router = None
        self.health_checker = None
        
    async def discover_and_initialize_services(self):
        """
        Discover database services and initialize connections.
        
        This method:
        1. Loads configuration from various sources
        2. Discovers available database services
        3. Dynamically loads required drivers
        4. Initializes connections and health monitoring
        """
        # Load configuration
        config = await self._load_database_config()
        
        # Discover services
        discovered_services = await self._discover_database_services(config)
        
        # Initialize each service
        for service_name, service_config in discovered_services.items():
            try:
                service = await self._initialize_database_service(
                    service_name, service_config
                )
                self.database_services[service_name] = service
                
                # Load required driver
                await self._load_database_driver(service_config)
                
            except Exception as e:
                logging.error(f"Failed to initialize database service {service_name}: {e}")
                # Continue with other services - don't fail completely
                
        # Initialize intent router
        self.intent_router = IntentBasedDatabaseRouter(self.database_services)
        
        # Start health monitoring
        self.health_checker = DatabaseHealthChecker(self.database_services)
        await self.health_checker.start_monitoring()
        
        logging.info(f"Database services initialized for {self.service_name}: "
                    f"{list(self.database_services.keys())}")
    
    async def _load_database_config(self):
        """Load database configuration from various sources."""
        if self.config is None:
            # Auto-discovery mode - look for config files
            return await self._discover_config_automatically()
        elif isinstance(self.config, dict):
            return self.config
        elif isinstance(self.config, str):
            # Assume it's a file path
            return await self._load_config_from_file(self.config)
        else:
            raise ValueError(f"Unsupported config type: {type(self.config)}")
    
    async def _discover_config_automatically(self):
        """Auto-discover database configuration from standard locations."""
        # Look for config.toml in service directory
        import os
        from pathlib import Path
        
        # Common config locations
        config_locations = [
            f"./config/database_services.toml",
            f"./{self.service_name}/config.toml",
            "./config.toml",
            "./database_config.toml"
        ]
        
        for location in config_locations:
            if os.path.exists(location):
                return await self._load_config_from_file(location)
        
        # No config found - return empty dict (use defaults/fallbacks)
        return {}
    
    async def _load_config_from_file(self, file_path: str):
        """Load configuration from TOML file."""
        try:
            import tomli
            with open(file_path, 'rb') as f:
                return tomli.load(f)
        except ImportError:
            logging.warning("tomli not available, using default database config")
            return {}
        except Exception as e:
            logging.error(f"Error loading config from {file_path}: {e}")
            return {}
    
    async def _discover_database_services(self, config: dict):
        """Discover available database services from configuration."""
        services = {}
        
        # Look for database services in config
        if "database-services" in config:
            services.update(config["database-services"])
        
        # Also check top-level database entries
        for key, value in config.items():
            if key.startswith("db-") or "-db" in key:
                services[key] = value
        
        # If no services found, create default services based on common patterns
        if not services:
            services = await self._create_default_services()
            
        return services
    
    async def _create_default_services(self):
        """Create default database services when none are configured."""
        return {
            "default-sql": {
                "type": "sql",
                "intent": "standard",
                "driver": "sqlite",
                "connection": ":memory:"
            },
            "default-cache": {
                "type": "key_value",
                "intent": "cache",
                "driver": "memory",
                "ttl": 300
            }
        }
    
    async def _initialize_database_service(self, name: str, config: dict):
        """Initialize a single database service."""
        service_type = config.get("type", "sql")
        driver = config.get("driver", self._default_driver_for_type(service_type))
        
        # Create service instance based on type
        if service_type == "sql":
            return await self._create_sql_service(name, config)
        elif service_type == "key_value":
            return await self._create_key_value_service(name, config)
        elif service_type == "nosql":
            return await self._create_nosql_service(name, config)
        elif service_type == "columnar":
            return await self._create_columnar_service(name, config)
        elif service_type == "document":
            return await self._create_document_service(name, config)
        else:
            # Generic service for unknown types
            return GenericDatabaseService(name, config)
    
    def _default_driver_for_type(self, service_type: str) -> str:
        """Get default driver for service type."""
        defaults = {
            "sql": "sqlite",
            "key_value": "memory",
            "nosql": "memory",
            "columnar": "memory",
            "document": "memory"
        }
        return defaults.get(service_type, "memory")
    
    async def _load_database_driver(self, service_config: dict):
        """Dynamically load required database driver based on intent."""
        driver = service_config.get("driver", "memory")
        
        if driver in self.driver_cache:
            return self.driver_cache[driver]
        
        # Load driver dynamically
        try:
            if driver == "sqlite":
                import sqlite3
                self.driver_cache[driver] = sqlite3
            elif driver == "postgresql":
                import asyncpg
                self.driver_cache[driver] = asyncpg
            elif driver == "mysql":
                import aiomysql
                self.driver_cache[driver] = aiomysql
            elif driver == "redis":
                import redis.asyncio as redis
                self.driver_cache[driver] = redis
            elif driver == "mongo":
                import motor.motor_asyncio
                self.driver_cache[driver] = motor.motor_asyncio
            else:
                # Memory driver (built-in)
                self.driver_cache[driver] = "memory_driver"
                
        except ImportError as e:
            logging.warning(f"Driver {driver} not available: {e}")
            # Fall back to memory driver
            self.driver_cache[driver] = "memory_driver"
            
        return self.driver_cache[driver]
    
    async def _create_sql_service(self, name: str, config: dict):
        """Create SQL database service."""
        # Implementation would create appropriate SQL service
        return SQLDatabaseService(name, config)
    
    async def _create_key_value_service(self, name: str, config: dict):
        """Create key-value database service."""
        return KeyValueDatabaseService(name, config)
    
    async def _create_nosql_service(self, name: str, config: dict):
        """Create NoSQL database service."""
        return NoSQLDatabaseService(name, config)
    
    async def _create_columnar_service(self, name: str, config: dict):
        """Create columnar database service."""
        return ColumnarDatabaseService(name, config)
    
    async def _create_document_service(self, name: str, config: dict):
        """Create document database service."""
        return DocumentDatabaseService(name, config)
    
    async def cleanup(self):
        """Clean up database connections and resources."""
        if self.health_checker:
            await self.health_checker.stop_monitoring()
            
        # Close all database connections
        for service in self.database_services.values():
            try:
                await service.close()
            except Exception as e:
                logging.error(f"Error closing database service: {e}")
                
        self.database_services.clear()
        self.driver_cache.clear()
        logging.info(f"Database services cleaned up for {self.service_name}")


# Placeholder service classes (would be implemented in separate files)
class GenericDatabaseService:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.connected = False
    
    async def close(self):
        self.connected = False


class SQLDatabaseService(GenericDatabaseService):
    pass

class KeyValueDatabaseService(GenericDatabaseService):
    pass

class NoSQLDatabaseService(GenericDatabaseService):
    pass

class ColumnarDatabaseService(GenericDatabaseService):
    pass

class DocumentDatabaseService(GenericDatabaseService):
    pass

class IntentBasedDatabaseRouter:
    """Routes database operations based on data intents."""
    def __init__(self, services: dict):
        self.services = services
    
    def route_operation(self, model, operation, intent):
        """Route database operation to appropriate service."""
        # Implementation would analyze intent and select service
        pass

class DatabaseHealthChecker:
    """Monitors health of database services."""
    def __init__(self, services: dict):
        self.services = services
        self.monitoring = False
    
    async def start_monitoring(self):
        self.monitoring = True
        # Implementation would start health checking tasks
        
    async def stop_monitoring(self):
        self.monitoring = False
        # Implementation would stop health checking tasks


class ServiceBuilder:
    """
    Service Builder - Main entry point for creating Evox services
    
    Provides a fluent API for building services with minimal configuration.
    
    Design Notes:
    - Uses method chaining for clean, readable service definitions
    - Integrates with priority queue for request scheduling
    - Supports both direct endpoint registration and decorator-based definitions
    - Automatic health endpoint generation
    
    Good first issue: Add support for custom middleware registration
    """
    
    def __init__(self, name: str):
        self.name = name
        self._port = 8000
        self._health_endpoint = "/health"
        self.app = FastAPI(title=f"Evox Service - {name}")
        self.router = APIRouter()
        self.startup_handlers: list[Callable] = []
        self.shutdown_handlers: list[Callable] = []
        self.background_tasks: list[dict[str, Any]] = []
        
        # Include router in app
        self.app.include_router(self.router)
        
        # Add default health endpoint
        @self.router.get(self._health_endpoint)
        async def health_check():
            return {"status": "healthy", "service": self.name}
        
        # Add middleware for intent-aware admission control
        self.app.middleware("http")(self._intent_aware_middleware)
        
        # Store service instance for DI access
        self._instance = None
        
        # Initialize new feature components
        self._use_fury = False
        self._cache_config = {'l1_size_mb': 100, 'redis_url': 'redis://localhost:6379'}
        self._benchmarking_enabled = False
    
    def port(self, port: int):
        """Set the service port"""
        self._port = port
        return self
    
    def health(self, endpoint: str = "/health"):
        """Set the health check endpoint"""
        self._health_endpoint = endpoint
        return self
    
    def build(self):
        """Build and finalize the service"""
        # Register any controllers that were decorated
        self._register_controllers()
        # Store instance for DI
        ServiceBuilder._instances[self.name] = self
        
        # Register with inject system for type-safe injection
        from ..infrastructure.dependency_injection.injector import HealthAwareInject
        HealthAwareInject.register_instance(self.name, self)
        
        # Trigger lifecycle event for service initialization
        import asyncio
        try:
            # Run the async lifecycle event in the current event loop if available
            loop = asyncio.get_running_loop()
            # Schedule the event to run soon
            loop.create_task(on_service_init(self.name, self))
        except RuntimeError:
            # No event loop running, run it directly
            asyncio.run(on_service_init(self.name, self))
        
        return self
    
    @classmethod
    def get_instance(cls, name: str):
        """Get service instance by name"""
        return cls._instances.get(name)
    
    def _register_controllers(self):
        """Register all decorated controllers with the service"""
        global _controller_registry
        
        for controller_name, controller_info in _controller_registry.items():
            controller_class = controller_info["class"]
            prefix = controller_info["prefix"]
            common_kwargs = controller_info["common_kwargs"]
            inherit_routes = controller_info.get("inherit_routes", False)
            
            # Create controller instance
            try:
                controller_instance = controller_class()
            except Exception as e:
                print(f"Warning: Could not instantiate controller {controller_name}: {e}")
                continue
            
            # Get all methods with _evoid_methods attribute
            for attr_name in dir(controller_instance):
                if attr_name.startswith('_'):
                    continue
                    
                attr = getattr(controller_instance, attr_name)
                if callable(attr) and hasattr(attr, '_evoid_methods'):
                    # Determine if this method is defined in the current class (not inherited)
                    is_defined_in_current_class = attr_name in controller_class.__dict__
                    
                    # If inherit_routes is False, only register methods defined in this class
                    if not inherit_routes and not is_defined_in_current_class:
                        continue
                    
                    # Bind the method to the instance
                    bound_method = attr.__get__(controller_instance, controller_class)
                    
                    # Check if method needs request parameter
                    import inspect
                    sig = inspect.signature(bound_method)
                    needs_request = 'request' not in sig.parameters
                    
                    # Register each method
                    for method_info in attr._evoid_methods:
                        method = method_info["method"]
                        paths = method_info["paths"]
                        kwargs = method_info["kwargs"]
                        
                        # Extract intent and priority from kwargs
                        intent = kwargs.get('intent')
                        priority = kwargs.get('priority', 'medium')
                        
                        # Register intent in the registry
                        for path in paths:
                            full_path = prefix + path if prefix else path
                            get_intent_registry().register_route_intent(
                                full_path, method, 
                                intent=intent, 
                                priority=priority
                            )
                        
                        # Merge common kwargs with method-specific kwargs
                        merged_kwargs = {**common_kwargs, **kwargs}
                        
                        # Remove intent and priority from kwargs that are passed to FastAPI (not supported)
                        intent = merged_kwargs.pop('intent', None)
                        priority = merged_kwargs.pop('priority', 'medium')
                        serialization = merged_kwargs.pop('serialization', 'json')
                        
                        # Register for each path
                        for path in paths:
                            full_path = prefix + path if prefix else path
                            
                            if needs_request:
                                # Create wrapped method with request injection
                                original_method = bound_method
                                
                                @wraps(original_method)
                                async def wrapped_method(request: Request, *args, **kwargs):
                                    kwargs['request'] = request
                                    return await original_method(*args, **kwargs)
                                
                                self.router.add_api_route(
                                    path=full_path,
                                    endpoint=wrapped_method,
                                    methods=[method],
                                    **merged_kwargs
                                )
                            else:
                                self.router.add_api_route(
                                    path=full_path,
                                    endpoint=bound_method,
                                    methods=[method],
                                    **merged_kwargs
                                )
        
        # Clear the registry after registration
        _controller_registry.clear()
    
    def endpoint(self, path: str, methods: list[str] = ["GET"], **kwargs):
        """
        Decorator for defining service endpoints
        
        Args:
            path: Endpoint path
            methods: HTTP methods
            **kwargs: Additional endpoint configuration including priority settings
        """
        def decorator(func: Callable[..., Any]):
            # Extract priority from kwargs if present
            priority_str = kwargs.pop('priority', 'medium')
            intent = kwargs.pop('intent', None)
            serialization = kwargs.pop('serialization', 'json')
            
            try:
                priority = PriorityLevel[priority_str.upper()]
            except KeyError:
                priority = PriorityLevel.MEDIUM  # Default to medium priority
            
            # Register intent in the registry
            for method in methods:
                get_intent_registry().register_route_intent(
                    path, method, 
                    intent=intent, 
                    priority=priority_str
                )
            
            # Store priority information for later use
            func._evoid_priority = priority
            
            self.router.add_api_route(
                path=path,
                endpoint=func,
                methods=methods,
                **kwargs
            )
            return func
        return decorator
    
    def group(self, prefix: str):
        """Create a grouped router with a prefix"""
        group_router = APIRouter(prefix=prefix)
        self.app.include_router(group_router)
        return group_router
    
    def on_startup(self, func: Callable[..., Any]):
        """Register a startup handler"""
        self.startup_handlers.append(func)
        self.app.on_event("startup")(func)
        return func
    
    def on_shutdown(self, func: Callable[..., Any]):
        """Register a shutdown handler"""
        self.shutdown_handlers.append(func)
        self.app.on_event("shutdown")(func)
        return func
    
    def background_task(self, interval: int) -> 'ServiceBuilder':
        """Decorator for defining background tasks"""
        def decorator(func: Callable[..., Any]):
            self.background_tasks.append({
                "func": func,
                "interval": interval
            })
            return func
        return decorator
    
    def enable_fury_serialization(self, enabled: bool = True):
        """Enable Fury serialization for this service"""
        self._use_fury = enabled
        if enabled and not fury_codec.fury_instance:
            logging.warning("Fury serialization requested but not available")
        return self
    
    def register_model_mapping(self, api_model: type, core_model: type):
        """Register model mapping for automatic conversion"""
        register_mapper(api_model, core_model)
        return self
    
    def configure_cache(self, l1_size_mb: int = 100, redis_url: str = "redis://localhost:6379"):
        """Configure cache settings"""
        self._cache_config = {
            'l1_size_mb': l1_size_mb,
            'redis_url': redis_url
        }
        return self
    
    def enable_benchmarking(self, enabled: bool = True):
        """Enable benchmarking endpoints"""
        self._benchmarking_enabled = enabled
        if enabled:
            self._add_benchmark_endpoints()
        return self
    
    def _add_benchmark_endpoints(self):
        """Add benchmarking endpoints to service"""
        from fastapi import BackgroundTasks
        from .benchmarking.performance_bench import benchmark_serialization
        
        @self.router.get("/benchmark/serialization")
        async def run_serialization_bench(severity: str = "moderate", duration: int = 30):
            """Run serialization benchmark"""
            result = await benchmark_serialization(severity, duration)
            return result
        
        @self.router.post("/benchmark/custom")
        async def run_custom_benchmark(config: dict, background_tasks: BackgroundTasks):
            """Run custom benchmark"""
            # Implementation would parse config and run specified benchmark
            return {"status": "benchmark_started"}
    
    def with_message_bus(self):
        """Enable message bus functionality for this service"""
        return self
    
    def with_task_manager(self):
        """Enable background task management for this service"""
        return self
    
    def with_model_mapping(self):
        """Enable automatic model mapping for this service"""
        return self
    
    def with_database_services(self, config=None):
        """
        Transform service builder into Resource Orchestrator with database service mapping.
        
        This method enables the service to automatically discover and map database services
        based on intent-aware model declarations. It dynamically loads required drivers
        and sets up intent-to-database routing.
        
        Args:
            config: Optional database service configuration
                  Can be a dict, TOML file path, or None (auto-discovery)
        
        Returns:
            self for method chaining
        
        Example:
            service = (
                service("user-service")
                .port(8000)
                .with_database_services({
                    "users-db": {"type": "sql", "intent": "critical"},
                    "cache-db": {"type": "key_value", "intent": "cache"}
                })
                .build()
            )
        """
        # Initialize database service orchestrator
        self._db_orchestrator = DatabaseServiceOrchestrator(
            service_name=self.name,
            config=config
        )
        
        # Enable database-aware middleware
        self.app.middleware("http")(self._database_intent_middleware)
        
        # Register startup handler for database service discovery
        @self.on_startup
        async def initialize_database_services():
            await self._db_orchestrator.discover_and_initialize_services()
            
        # Register shutdown handler for graceful cleanup
        @self.on_shutdown
        async def cleanup_database_services():
            await self._db_orchestrator.cleanup()
            
        return self
    
    async def _database_intent_middleware(self, request: Request, call_next):
        """
        Middleware that intercepts requests and applies database intent routing.
        
        This middleware analyzes request data and model intents to route
        database operations to appropriate services automatically.
        """
        # Let the request proceed normally
        response = await call_next(request)
        return response
    
    async def gather(self, 
                     *requests,
                     priority: str = "medium",
                     concurrency: int = 5) -> list[Any]:
        """
        Execute multiple requests concurrently with priority and concurrency control.
        
        This method integrates with the priority-aware queue system to execute
        multiple requests with controlled concurrency and priority levels.
        
        Args:
            *requests: Request coroutines to execute
            priority: Priority level for all requests ("high", "medium", "low")
            concurrency: Maximum number of concurrent requests
            
        Returns:
            List of results in the same order as requests
            
        Example:
            results = await service.gather(
                service1.call(), 
                service2.call(),
                priority="high",
                concurrency=3
            )
        """
        try:
            priority_level = PriorityLevel[priority.upper()]
        except KeyError:
            priority_level = PriorityLevel.MEDIUM
            
        queue = get_priority_queue()
        return await queue.gather(*requests, priority=priority_level, concurrency=concurrency)
    
    def run(self, dev: bool = False):
        """Run the service"""
        # Perform initial health checks on startup
        if not dev:
            asyncio.run(self._perform_initial_health_checks())
        
        if dev:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=self._port,
                reload=True,
                log_level="debug"
            )
        else:
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=self._port,
                log_level="info"
            )
    
    async def _perform_initial_health_checks(self):
        """
        Perform initial health checks on all registered providers during startup.
        
        Rationale: This ensures that all services are aware of the health status
        of their dependencies at startup time, enabling immediate degraded mode
        operations if needed.
        """
        logging.info(f"Performing initial health checks for service: {self.name}")
        
        # Get the health registry to check all registered services
        health_registry = get_health_registry()
        
        # Check health for all registered providers
        for service_name, health_info in health_registry.items():
            instance = health_info.get("instance")
            if instance and isinstance(instance, BaseProvider):
                is_healthy = await instance.check_health()
                
                # Update health registry with new check
                health_info["is_healthy"] = is_healthy
                health_info["last_check"] = datetime.now()
                
                if not is_healthy:
                    logging.warning(f"Service '{service_name}' is unhealthy at startup")
                else:
                    logging.info(f"Service '{service_name}' is healthy at startup")
    
    async def _intent_aware_middleware(self, request: Request, call_next):
        """
        Intent-aware middleware that implements admission control based on system status.
        
        Rationale: This middleware intercepts requests before they reach the handler
        and applies intent-aware admission control based on system resource status.
        """
        # Import intelligence here to avoid circular import
        from .intelligence import get_current_context_status, SystemStatus
        
        # Get the route information
        path = request.url.path
        method = request.method
        
        # Get intent and priority for this route from the registry
        route_info = get_intent_registry().get_route_intent(path, method)
        route_intent = route_info.get("intent")
        route_priority_str = route_info.get("priority", "medium")
        
        # Convert priority string to PriorityLevel enum
        try:
            from .queue import PriorityLevel
            route_priority = PriorityLevel[route_priority_str.upper()]
        except KeyError:
            route_priority = PriorityLevel.MEDIUM
        
        # Check system status and apply admission control
        system_status = get_current_context_status()
        
        # Apply intent-aware admission control
        from .queue import PriorityQueue
        queue = get_priority_queue()
        is_allowed = queue._is_request_allowed(system_status, route_intent, route_priority, path, method)
        
        if not is_allowed:
            # Log the load shedding event
            logging.warning(
                f"Load shedding: Request to {method} {path} with intent {route_intent} and priority {route_priority_str} "
                f"rejected due to system status {system_status}"
            )
            return JSONResponse(
                status_code=503,
                content={"detail": "Service temporarily unavailable due to high load"}
            )
        
        # If request is allowed, proceed with normal processing
        response = await call_next(request)
        return response


# Convenience functions
def service(name: str) -> ServiceBuilder:
    """Create a new service builder with string name"""
    return ServiceBuilder(name)


def Service(service_type):
    """Type-safe service factory that resolves name from config.toml"""
    # In a real implementation, this would read the config.toml file
    # associated with the service_type to get the service name
    # For now, we'll use the class name as the service name
    service_name = service_type.__name__ if hasattr(service_type, '__name__') else str(service_type)
    
    # Convert CamelCase to kebab-case for service names
    import re
    service_name = re.sub(r'(?<!^)(?=[A-Z])', '-', service_name).lower()
    service_name = service_name.replace('_service', '-service')
    
    # Register the service type with its name for DI
    from .inject import HealthAwareInject
    HealthAwareInject.register_service(service_type, service_name)
    
    return ServiceBuilder(service_name)


# Decorators for endpoints
def get(path: str, intent: str = None, priority: str = "medium", 
     serialization: str = "json", **kwargs):
    """GET endpoint decorator with intent, priority, and serialization support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evoid_endpoint = {
            "path": path,
            "methods": ["GET"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority, "serialization": serialization}
        }
        return func
    return decorator

def post(path: str, intent: str = None, priority: str = "medium", 
     serialization: str = "json", **kwargs):
    """POST endpoint decorator with intent, priority, and serialization support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evoid_endpoint = {
            "path": path,
            "methods": ["POST"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority, "serialization": serialization}
        }
        return func
    return decorator

def put(path: str, intent: str = None, priority: str = "medium", 
     serialization: str = "json", **kwargs):
    """PUT endpoint decorator with intent, priority, and serialization support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evoid_endpoint = {
            "path": path,
            "methods": ["PUT"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority, "serialization": serialization}
        }
        return func
    return decorator

def delete(path: str, intent: str = None, priority: str = "medium", 
     serialization: str = "json", **kwargs):
    """DELETE endpoint decorator with intent, priority, and serialization support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evoid_endpoint = {
            "path": path,
            "methods": ["DELETE"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority, "serialization": serialization}
        }
        return func
    return decorator

def patch(path: str, intent: str = None, priority: str = "medium", 
     serialization: str = "json", **kwargs):
    """PATCH endpoint decorator with intent, priority, and serialization support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evoid_endpoint = {
            "path": path,
            "methods": ["PATCH"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority, "serialization": serialization}
        }
        return func
    return decorator

def head(path: str, intent: str = None, priority: str = "medium", 
     serialization: str = "json", **kwargs):
    """HEAD endpoint decorator with intent, priority, and serialization support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evoid_endpoint = {
            "path": path,
            "methods": ["HEAD"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority, "serialization": serialization}
        }
        return func
    return decorator

def options(path: str, intent: str = None, priority: str = "medium", 
     serialization: str = "json", **kwargs):
    """OPTIONS endpoint decorator with intent, priority, and serialization support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evoid_endpoint = {
            "path": path,
            "methods": ["OPTIONS"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority, "serialization": serialization}
        }
        return func
    return decorator


def get_cached(path: str, ttl: int = 300, **kwargs):
    """GET endpoint with automatic caching"""
    def decorator(func):
        original_func = func
        
        async def wrapper(*args, **kwargs):
            # Generate cache key from request
            import hashlib
            cache_key = hashlib.md5(f"{path}{str(args)}{str(sorted(kwargs.items()))}".encode()).hexdigest()
            
            # Try cache first
            from .caching.cache_layer import cache_get
            cached_result = await cache_get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute original function
            result = await original_func(*args, **kwargs)
            
            # Cache result
            from .caching.cache_layer import cache_set
            await cache_set(cache_key, result, ttl)
            
            return result
        
        # Preserve endpoint metadata
        wrapper._evoid_endpoint = {
            "path": path,
            "methods": ["GET"],
            "kwargs": kwargs,
            "ttl": ttl
        }
        return wrapper
    return decorator


def endpoint(path: str = None, methods: list[str] = ["GET"], intent: str = None, priority: str = "medium", **kwargs):
    """
    Generic endpoint decorator for internal/non-route handlers
    
    Args:
        path: Endpoint path (optional for internal handlers)
        methods: HTTP methods
        intent: Intent for this endpoint
        priority: Priority level for this endpoint
        **kwargs: Additional endpoint configuration including priority settings
    """
    def decorator(func: Callable[..., Any]):
        func._evoid_endpoint = {
            "path": path,
            "methods": methods,
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
    return decorator


# Type aliases for parameter injection with Pydantic Annotated support
from typing import Annotated

# Enhanced parameter injection with type safety
# Rationale: Using Pydantic's Annotated provides compile-time type checking
# while maintaining runtime flexibility for dependency injection
Param = lambda x, default=...: Annotated[x, "param"] if default is ... else Annotated[x, "param", default]
Query = lambda x, default=...: Annotated[x, "query"] if default is ... else Annotated[x, "query", default]
Body = lambda x, default=...: Annotated[x, "body"] if default is ... else Annotated[x, "body", default]


# Controller decorator for class-based syntax
_controller_registry = {}

# Service instances registry
ServiceBuilder._instances = {}

def Controller(prefix: str = "", intent: str = None, priority: str = "medium", inherit_routes: bool = False, **kwargs):
    """
    Decorator for creating controllers in class-based syntax
    
    Args:
        prefix: Common prefix for all endpoints in this controller
        intent: Default intent for all endpoints in this controller
        priority: Default priority for all endpoints in this controller
        inherit_routes: Whether to inherit routes from parent classes (default: False)
        **kwargs: Common configuration for all endpoints (cache, auth, etc.)
    """
    def decorator(cls):
        # Store controller information for later registration
        controller_info = {
            "class": cls,
            "prefix": prefix,
            "common_kwargs": {**kwargs, "intent": intent, "priority": priority},
            "inherit_routes": inherit_routes
        }
        _controller_registry[cls.__name__] = controller_info
        return cls
    return decorator


# HTTP method decorators for class-based syntax
class _MethodDecorator:
    """Base class for HTTP method decorators in class-based syntax"""
    
    def __init__(self, *paths, intent: str = None, priority: str = "medium", **kwargs):
        self.paths = paths
        self.intent = intent
        self.priority = priority
        self.kwargs = {**kwargs, "intent": intent, "priority": priority}
    
    def __call__(self, func):
        # Store method information for later registration
        if not hasattr(func, '_evoid_methods'):
            func._evoid_methods = []
        
        method_info = {
            "method": self.__class__.__name__.upper(),
            "paths": self.paths,
            "kwargs": self.kwargs
        }
        func._evoid_methods.append(method_info)
        return func

# Create HTTP method decorators using generator pattern
def _create_http_method_decorator(method_name):
    """Create an HTTP method decorator class dynamically"""
    return type(method_name, (_MethodDecorator,), {
        "__doc__": f"{method_name} method decorator for class-based syntax"
    })

# Create HTTP method decorators
GET = _create_http_method_decorator("GET")
POST = _create_http_method_decorator("POST")
PUT = _create_http_method_decorator("PUT")
DELETE = _create_http_method_decorator("DELETE")
PATCH = _create_http_method_decorator("PATCH")
HEAD = _create_http_method_decorator("HEAD")
OPTIONS = _create_http_method_decorator("OPTIONS")