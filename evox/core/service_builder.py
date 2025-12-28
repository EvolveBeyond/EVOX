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

from .queue import PriorityLevel, get_priority_queue
from .inject import get_health_registry, get_service_health
from .common import BaseProvider
from .intents import Intent, get_intent_registry
from .lifecycle import on_service_init


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
        from .inject import HealthAwareInject
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
            
            # Get all methods with _evox_methods attribute
            for attr_name in dir(controller_instance):
                if attr_name.startswith('_'):
                    continue
                    
                attr = getattr(controller_instance, attr_name)
                if callable(attr) and hasattr(attr, '_evox_methods'):
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
                    for method_info in attr._evox_methods:
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
            func._evox_priority = priority
            
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
def get(path: str, intent: str = None, priority: str = "medium", **kwargs):
    """GET endpoint decorator with intent and priority support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["GET"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
    return decorator

def post(path: str, intent: str = None, priority: str = "medium", **kwargs):
    """POST endpoint decorator with intent and priority support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["POST"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
    return decorator

def put(path: str, intent: str = None, priority: str = "medium", **kwargs):
    """PUT endpoint decorator with intent and priority support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["PUT"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
    return decorator

def delete(path: str, intent: str = None, priority: str = "medium", **kwargs):
    """DELETE endpoint decorator with intent and priority support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["DELETE"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
    return decorator

def patch(path: str, intent: str = None, priority: str = "medium", **kwargs):
    """PATCH endpoint decorator with intent and priority support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["PATCH"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
    return decorator

def head(path: str, intent: str = None, priority: str = "medium", **kwargs):
    """HEAD endpoint decorator with intent and priority support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["HEAD"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
    return decorator

def options(path: str, intent: str = None, priority: str = "medium", **kwargs):
    """OPTIONS endpoint decorator with intent and priority support"""
    def decorator(func: Callable[..., Any]):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["OPTIONS"],
            "kwargs": {**kwargs, "intent": intent, "priority": priority}
        }
        return func
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
        func._evox_endpoint = {
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
        if not hasattr(func, '_evox_methods'):
            func._evox_methods = []
        
        method_info = {
            "method": self.__class__.__name__.upper(),
            "paths": self.paths,
            "kwargs": self.kwargs
        }
        func._evox_methods.append(method_info)
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