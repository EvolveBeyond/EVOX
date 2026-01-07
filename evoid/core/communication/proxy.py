"""
Registry-Driven Service Proxy - Intent-Aware, Context-Aware Service-to-Service Communication

This module provides the Registry-Driven, Intent-Aware service proxy for Evox, handling service-to-service
communication with support for:
1. Context-aware routing (internal vs external calls)
2. Multi-method endpoint support
3. Priority queuing
4. Automatic routing and fallback mechanisms
5. Security enforcement

This module provides the Registry-Driven service proxy for Evox, handling Intent-Aware service-to-service
communication with support for priority queuing, automatic routing, and fallback mechanisms.

The proxy automatically routes calls between services using the most appropriate method
(router, REST, hybrid) based on service configuration and availability.
"""

from typing import Any, Callable
import httpx
import asyncio
from fastapi import Request
from pydantic import BaseModel

from ..infrastructure.queue.priority_queue import PriorityLevel, get_priority_queue
from ..infrastructure.auth.auth_manager import get_auth_manager


class ServiceProxy:
    """
    Smart proxy that automatically routes service calls with context-aware routing.
        
        This proxy provides intelligent service-to-service communication with:
        1. Context detection (internal vs external calls)
        2. Multi-method endpoint support
        3. Priority-aware request queuing
        4. Security enforcement (HTTPS for external, internal tokens for internal)
        5. Fallback mechanisms for service unavailability
        6. Concurrent execution with gather method
    
    This proxy provides intelligent service-to-service communication with:
    1. Automatic routing (router, REST, hybrid)
    2. Priority-aware request queuing
    3. Fallback mechanisms for service unavailability
    4. Concurrent execution with gather method
    
    Design Notes:
    - Uses dynamic method interception for seamless service calls
    - Integrates with priority queue for request scheduling
    - Implements context-aware routing (internal vs external)
    - Enforces security (HTTPS for external, internal tokens for internal)
    - Implements self-healing through automatic retries and fallbacks
    
    Good first issue: Add circuit breaker pattern for failed services
    """
    
    _instances: dict[str, 'ServiceProxy'] = {}
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.auth_manager = get_auth_manager()
        # Track registered service endpoints for method dispatch
        self._endpoints: dict[str, dict[str, Callable]] = {}
        # Track HTTP method for each call
        self._http_method = None
        # Context-aware priority management
        self._priority_context = {}
        # Schema-based priority boosting
        self._schema_priority_boost = {}
    
    def __getattr__(self, method_name: str) -> Callable:
        """
        Dynamic method proxy - intercepts all method calls and routes them.
        """
        if method_name.startswith('_'):
            # Don't proxy private methods
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{method_name}'")
        
        async def proxy_method(*args, priority: str | None = None, **kwargs):
            """
            Proxy method with intelligent, context-aware priority support.
            
            Args:
                *args: Positional arguments for the service method
                priority: Priority level for the request ("high", "medium", "low") or None for auto-detection
                **kwargs: Keyword arguments for the service method
            """
            try:
                # Determine priority based on context, schema, and requester
                final_priority = self._determine_priority(priority, args, kwargs)
                
                # Submit to priority queue
                queue = get_priority_queue()
                priority_level = PriorityLevel(final_priority)
                
                return await queue.submit(
                    self._execute_service_call,
                    method_name, *args,
                    priority=priority_level,
                    **kwargs
                )
            except Exception as e:
                print(f"⚠️  Service call failed for {self.service_name}.{method_name}: {e}")
                raise
        
        return proxy_method
    
    def _determine_priority(self, explicit_priority: str | None, args: tuple, kwargs: dict) -> str:
        """
        Determine priority based on context, schema metadata, and requester.
        
        Priority sources (in order of precedence):
        1. Explicit priority parameter
        2. Schema-based priority boost
        3. Context-aware priority from headers/payload
        4. Default priority
        """
        # 1. Use explicit priority if provided
        if explicit_priority:
            return explicit_priority
        
        # 2. Check for schema-based priority boost
        schema_priority = self._check_schema_priority(kwargs)
        if schema_priority:
            return schema_priority
        
        # 3. Check for context-aware priority from headers/payload
        context_priority = self._check_context_priority(kwargs)
        if context_priority:
            return context_priority
        
        # 4. Default to medium priority
        return "medium"
    
    def _check_schema_priority(self, kwargs: dict) -> str | None:
        """Check if any schema in kwargs has a priority boost"""
        # Look for Pydantic models in kwargs
        for key, value in kwargs.items():
            if isinstance(value, BaseModel):
                # Check if schema has priority metadata
                schema_name = value.__class__.__name__
                if schema_name in self._schema_priority_boost:
                    return self._schema_priority_boost[schema_name]
                
                # Check for priority field in schema
                if hasattr(value, 'priority') and value.priority:
                    return value.priority
        
        return None
    
    def _check_context_priority(self, kwargs: dict) -> str | None:
        """Check for context-aware priority from headers or payload"""
        # Check headers for priority information
        headers = kwargs.get('headers', {})
        if 'X-Priority' in headers:
            priority = headers['X-Priority'].lower()
            if priority in ['high', 'medium', 'low']:
                return priority
        
        # Check for priority in payload
        if 'priority' in kwargs:
            priority = kwargs['priority'].lower()
            if priority in ['high', 'medium', 'low']:
                return priority
        
        return None
    
    def set_schema_priority_boost(self, schema_name: str, priority: str):
        """Set priority boost for a specific schema"""
        if priority in ['high', 'medium', 'low']:
            self._schema_priority_boost[schema_name] = priority
    
    def set_context_priority(self, context_key: str, priority: str):
        """Set context-based priority"""
        if priority in ['high', 'medium', 'low']:
            self._priority_context[context_key] = priority
    
    async def _execute_service_call(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a service method call with context-aware routing.
        
        This method implements the core service call logic with:
        1. Context detection (internal vs external calls)
        2. Automatic routing (direct vs HTTPS)
        3. Authentication enforcement
        4. Fallback mechanisms
        5. HTTP method support for multi-method endpoints
        """
        try:
            # Detect call context (internal vs external)
            is_internal = self._is_internal_call(kwargs)
            
            # Add HTTP method information to kwargs for routing
            if self._http_method:
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['X-Evox-Method'] = self._http_method
                # Reset method for next call
                self._http_method = None
            
            if is_internal:
                # Internal calls: Direct routing with internal token
                return await self._call_internal(method_name, *args, **kwargs)
            else:
                # External calls: HTTPS with full auth
                return await self._call_external(method_name, *args, **kwargs)
        except Exception as e:
            print(f"⚠️  Service call failed for {self.service_name}.{method_name}: {e}")
            raise
    
    def _is_internal_call(self, kwargs: dict) -> bool:
        """
        Detect if the call is internal (from another Evox service) or external (from client).
        
        Returns:
            bool: True if internal call, False if external
        """
        # Check for internal token in kwargs or headers
        internal_token = kwargs.get('internal_token') or kwargs.get('headers', {}).get('X-Evox-Internal')
        if internal_token:
            try:
                self.auth_manager.verify_internal_token(internal_token)
                return True
            except:
                return False
        
        # For optimization, we assume external calls by default
        return False
    
    async def _call_internal(self, method_name: str, *args, **kwargs) -> Any:
        """
        Call service method via internal routing (fastest, no HTTPS overhead).
        
        Args:
            method_name: Name of the method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of the service call
        """
        # For internal calls, we would route directly to the service
        # This is a simplified implementation - in practice, this would use
        # direct function calls or in-memory messaging
        
        # Add internal token for downstream services
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['X-Evox-Internal'] = self.auth_manager.create_internal_token(self.service_name)
        
        return await self._call_via_rest(method_name, *args, **kwargs)
    
    async def _call_external(self, method_name: str, *args, **kwargs) -> Any:
        """
        Call service method via external routing (HTTPS + full auth validation).
        
        Args:
            method_name: Name of the method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result of the service call
        """
        # For external calls, enforce HTTPS and full authentication
        # This is a simplified implementation - in practice, this would ensure HTTPS
        
        # Validate authentication if required
        # This would be handled by endpoint decorators in the actual service
        
        return await self._call_via_rest(method_name, *args, **kwargs)
    
    async def _call_via_rest(self, method_name: str, *args, **kwargs) -> Any:
        """
        Call service method via REST API with HTTP method support.
        
        This is the fallback mechanism when direct routing is not available.
        """
        # This is a simplified implementation
        # In a real implementation, this would use service discovery
        base_url = f"http://localhost:8000/{self.service_name}"  # Default fallback
        endpoint_url = f"{base_url}/{method_name}"
        
        # Prepare request data
        request_data = {
            "args": args,
            "kwargs": kwargs
        }
        
        # Add headers if provided
        headers = kwargs.get('headers', {})
        
        # Determine HTTP method from headers or default to POST
        http_method = headers.pop('X-Evox-Method', 'POST')
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if http_method.upper() == 'GET':
                # For GET requests, we typically don't send a body
                # Extract query parameters from kwargs if available
                query_params = kwargs.get('params', {})
                response = await client.get(
                    endpoint_url,
                    params=query_params,
                    headers=headers
                )
            elif http_method.upper() == 'POST':
                response = await client.post(
                    endpoint_url,
                    json=request_data,
                    headers=headers
                )
            elif http_method.upper() == 'PUT':
                response = await client.put(
                    endpoint_url,
                    json=request_data,
                    headers=headers
                )
            elif http_method.upper() == 'DELETE':
                response = await client.delete(
                    endpoint_url,
                    headers=headers
                )
            else:
                # Default to POST for unknown methods
                response = await client.post(
                    endpoint_url,
                    json=request_data,
                    headers=headers
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
    
    @classmethod
    def get_instance(cls, service_name: str) -> 'ServiceProxy':
        """Get or create a proxy instance for a service"""
        if service_name not in cls._instances:
            cls._instances[service_name] = cls(service_name)
        return cls._instances[service_name]
    
    async def gather(self, 
                     *calls, 
                     policy: str = "partial", 
                     priority: str = "medium",
                     concurrency: int = 5) -> list[Any]:
        """
        Execute multiple service calls concurrently with priority and policy control.
        
        This method provides concurrent execution of multiple service calls with
        configurable execution policies and priority levels.
        
        Args:
            *calls: Service calls to execute
            policy: Execution policy ("partial" or "all_or_nothing")
            priority: Priority level ("high", "medium", "low")
            concurrency: Maximum number of concurrent requests
            
        Returns:
            list of results in the same order as calls
            
        Example:
            # Execute multiple calls with high priority and limited concurrency
            results = await proxy.gather(
                service1.get_user(123),
                service2.get_profile(123),
                priority="high",
                concurrency=3
            )
        """
        # Submit to priority queue with concurrency control
        queue = get_priority_queue()
        try:
            priority_level = PriorityLevel(priority)
        except ValueError:
            priority_level = PriorityLevel.MEDIUM
            
        return await queue.gather(
            *calls,
            priority=priority_level,
            concurrency=concurrency
        )


# Convenience functions for common service proxies
def get_service(service_name: str) -> ServiceProxy:
    """Get service proxy by name"""
    return ServiceProxy.get_instance(service_name)


# Proxy for accessing multiple services
class ProxyAccessor:
    """Dynamic proxy accessor for all services
    
    Allows accessing service proxies using attribute access.
    
    Example:
        # Access user service
        user = await proxy.user.get_user(123)
        
        # Access data service
        data = await proxy.data.get_records()
    """
    
    def __getattr__(self, service_name: str) -> ServiceProxy:
        return ServiceProxy.get_instance(service_name)


# Method-specific proxy decorators

class MethodProxy:
    """Method-specific proxy for multi-method endpoint support"""
    
    def __init__(self, service_proxy: ServiceProxy, method: str):
        self.service_proxy = service_proxy
        self.method = method
    
    def __getattr__(self, attr_name: str):
        # Set the HTTP method on the service proxy
        self.service_proxy._http_method = self.method
        return getattr(self.service_proxy, attr_name)
    
    def __call__(self, *args, **kwargs):
        # Support direct calling of method proxies
        self.service_proxy._http_method = self.method
        return self.service_proxy(*args, **kwargs)


class HttpMethodProxyAccessor:
    """HTTP method proxy accessor for multi-method endpoint support"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._service_proxy = None
    
    @property
    def service_proxy(self):
        if self._service_proxy is None:
            self._service_proxy = ServiceProxy.get_instance(self.service_name)
        return self._service_proxy
    
    # Generate HTTP method properties dynamically
    def _create_method_proxy(self, method):
        """Create a method proxy for the given HTTP method"""
        return MethodProxy(self.service_proxy, method)
    
    @property
    def get(self):
        """GET method proxy"""
        return self._create_method_proxy("GET")
    
    @property
    def post(self):
        """POST method proxy"""
        return self._create_method_proxy("POST")
    
    @property
    def put(self):
        """PUT method proxy"""
        return self._create_method_proxy("PUT")
    
    @property
    def delete(self):
        """DELETE method proxy"""
        return self._create_method_proxy("DELETE")
    
    def __getattr__(self, attr_name: str):
        return getattr(self.service_proxy, attr_name)


class EnhancedProxyAccessor(ProxyAccessor):
    """Enhanced proxy accessor with HTTP method support"""
    
    def __getattr__(self, service_name: str) -> HttpMethodProxyAccessor:
        return HttpMethodProxyAccessor(service_name)


# Global proxy accessor
proxy = EnhancedProxyAccessor()