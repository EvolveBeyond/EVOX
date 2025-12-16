"""
Service Builder - Main entry point for creating Evox services

This module provides the fluent API for building Evox services with minimal configuration.
It supports priority-aware request queuing and aggressive cache fallback mechanisms.
"""

import asyncio
import uvicorn
from typing import Optional, Callable, Any, Dict, List, Type, Union
from fastapi import FastAPI, APIRouter, Request
from functools import wraps

from .queue import PriorityLevel, get_priority_queue


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
        self.startup_handlers: List[Callable] = []
        self.shutdown_handlers: List[Callable] = []
        self.background_tasks: List[Dict[str, Any]] = []
        
        # Include router in app
        self.app.include_router(self.router)
        
        # Add default health endpoint
        @self.router.get(self._health_endpoint)
        async def health_check():
            return {"status": "healthy", "service": self.name}
    
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
        return self
    
    def _register_controllers(self):
        """Register all decorated controllers with the service"""
        global _controller_registry
        
        for controller_name, controller_info in _controller_registry.items():
            controller_class = controller_info["class"]
            prefix = controller_info["prefix"]
            common_kwargs = controller_info["common_kwargs"]
            
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
    
    def endpoint(self, path: str, methods: List[str] = ["GET"], **kwargs):
        """
        Decorator for defining service endpoints
        
        Args:
            path: Endpoint path
            methods: HTTP methods
            **kwargs: Additional endpoint configuration including priority settings
        """
        def decorator(func: Callable):
            # Extract priority from kwargs if present
            priority_str = kwargs.pop('priority', 'medium')
            try:
                priority = PriorityLevel(priority_str)
            except ValueError:
                priority = PriorityLevel.MEDIUM  # Default to medium priority
            
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
    
    def on_startup(self, func: Callable):
        """Register a startup handler"""
        self.startup_handlers.append(func)
        self.app.on_event("startup")(func)
        return func
    
    def on_shutdown(self, func: Callable):
        """Register a shutdown handler"""
        self.shutdown_handlers.append(func)
        self.app.on_event("shutdown")(func)
        return func
    
    def background_task(self, interval: int):
        """Decorator for defining background tasks"""
        def decorator(func: Callable):
            self.background_tasks.append({
                "func": func,
                "interval": interval
            })
            return func
        return decorator
    
    async def gather(self, 
                     *requests,
                     priority: str = "medium",
                     concurrency: int = 5) -> List[Any]:
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
            priority_level = PriorityLevel(priority)
        except ValueError:
            priority_level = PriorityLevel.MEDIUM
            
        queue = get_priority_queue()
        return await queue.gather(*requests, priority=priority_level, concurrency=concurrency)
    
    def run(self, dev: bool = False):
        """Run the service"""
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


# Convenience functions
def service(name: str) -> ServiceBuilder:
    """Create a new service builder"""
    return ServiceBuilder(name)


# Decorators for endpoints
def get(path: str, **kwargs):
    """GET endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["GET"],
            "kwargs": kwargs
        }
        return func
    return decorator


def post(path: str, **kwargs):
    """POST endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["POST"],
            "kwargs": kwargs
        }
        return func
    return decorator


def put(path: str, **kwargs):
    """PUT endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["PUT"],
            "kwargs": kwargs
        }
        return func
    return decorator


def delete(path: str, **kwargs):
    """DELETE endpoint decorator with priority support"""
    def decorator(func: Callable):
        # This will be used by ServiceBuilder.endpoint
        func._evox_endpoint = {
            "path": path,
            "methods": ["DELETE"],
            "kwargs": kwargs
        }
        return func
    return decorator


def endpoint(path: str = None, methods: List[str] = ["GET"], **kwargs):
    """
    Generic endpoint decorator for internal/non-route handlers
    
    Args:
        path: Endpoint path (optional for internal handlers)
        methods: HTTP methods
        **kwargs: Additional endpoint configuration including priority settings
    """
    def decorator(func: Callable):
        func._evox_endpoint = {
            "path": path,
            "methods": methods,
            "kwargs": kwargs
        }
        return func
    return decorator


# Type aliases for parameter injection
Param = Union
Query = Union
Body = Union


# Controller decorator for class-based syntax
_controller_registry = {}

def Controller(prefix: str = "", **kwargs):
    """
    Decorator for creating controllers in class-based syntax
    
    Args:
        prefix: Common prefix for all endpoints in this controller
        **kwargs: Common configuration for all endpoints (cache, auth, etc.)
    """
    def decorator(cls):
        # Store controller information for later registration
        controller_info = {
            "class": cls,
            "prefix": prefix,
            "common_kwargs": kwargs
        }
        _controller_registry[cls.__name__] = controller_info
        return cls
    return decorator


# HTTP method decorators for class-based syntax
class _MethodDecorator:
    """Base class for HTTP method decorators in class-based syntax"""
    
    def __init__(self, *paths, **kwargs):
        self.paths = paths
        self.kwargs = kwargs
    
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


class GET(_MethodDecorator):
    """GET method decorator for class-based syntax"""
    pass


class POST(_MethodDecorator):
    """POST method decorator for class-based syntax"""
    pass


class PUT(_MethodDecorator):
    """PUT method decorator for class-based syntax"""
    pass


class DELETE(_MethodDecorator):
    """DELETE method decorator for class-based syntax"""
    pass


# Intent decorator for both syntaxes
class Intent:
    """Intent decorator for declaring data intent behavior"""
    
    def __init__(self, **kwargs):
        self.intent_config = kwargs
    
    def __call__(self, func_or_cls):
        """Apply intent to a function or class"""
        if hasattr(func_or_cls, '__dict__'):
            # Class-based: apply to all methods
            func_or_cls._evox_intent = self.intent_config
        else:
            # Function-based: apply to function
            func_or_cls._evox_intent = self.intent_config
        return func_or_cls
    
    @staticmethod
    def cacheable(ttl: Union[int, str] = 300, **kwargs):
        """Declare that data is cacheable"""
        intent_config = {
            "cacheable": True,
            "ttl": ttl,
            **kwargs
        }
        return Intent(**intent_config)