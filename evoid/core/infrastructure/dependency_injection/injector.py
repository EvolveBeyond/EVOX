"""
Registry-Driven Health-Aware Dependency Injection - Intent-Aware, Fully Pydantic-based injection system

This module provides a Registry-Driven, Intent-Aware type-safe, secure dependency injection system that:
- Uses Pydantic Annotated for all parameter and dependency injection
- Eliminates string-based injection vulnerabilities
- Provides lazy resolution with zero-cost initialization
- Supports comprehensive testing with override mechanisms
- Implements health awareness for providers with degraded mode capabilities
"""

from typing import TypeVar, Generic, get_origin, get_args, Dict, Any

from functools import wraps

from datetime import datetime
import contextvars
import asyncio
import logging
from typing import Annotated

# Import moved to avoid circular import
# BaseProvider is imported locally where needed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...data.storage.providers.base_provider import BaseProvider



# Global registry for service instances
_service_registry: dict[str, Any] = {}

# Global registry for service types to names mapping
_service_type_mapping: dict[type, str] = {}

# Context variable to track health state for the current execution context
_current_request_health_state = contextvars.ContextVar("current_request_health_state", default=None)

# Global registry for health states
_health_registry: dict[str, dict[str, Any]] = {}


class HealthProxy:
    """
    Proxy wrapper for unhealthy dependencies to enable degraded mode operations
    
    This proxy wraps an unhealthy dependency and logs warnings when it is used,
    allowing the application to continue operating in a degraded state.
    """
    
    def __init__(self, wrapped_instance: Any, service_name: str):
        self._wrapped_instance = wrapped_instance
        self._service_name = service_name
        
    def __getattr__(self, name):
        # Log a warning when accessing any attribute of an unhealthy service
        logging.warning(f"Accessing potentially unreliable service '{self._service_name}' in degraded mode")
        return getattr(self._wrapped_instance, name)


T = TypeVar('T')

class HealthAwareInject(Generic[T]):
    """
    Health-aware dependency injection system with degraded mode capabilities
    
    Provides lazy resolution of dependencies with full type safety using Pydantic Annotated.
    Implements health awareness for providers and degraded mode operations.
    """
    
    def __init__(self, dependency_type: type[T] | None = None, fallback_to: Any = None):
        self.dependency_type = dependency_type
        self.fallback_to = fallback_to
    
    @classmethod
    def register_service(cls, service_type: type, service_name: str):
        """Register a service type with its name from config.toml"""
        global _service_type_mapping
        _service_type_mapping[service_type] = service_name
    
    @classmethod
    def register_instance(cls, service_name: str, instance: Any):
        """Register a service instance"""
        global _service_registry
        _service_registry[service_name] = instance

    @classmethod
    def register_health_state(cls, service_name: str, health_state: Dict[str, Any]):
        """Register health state for a service"""
        global _health_registry
        _health_registry[service_name] = health_state
    
    async def __call__(self) -> T:
        """
        Securely inject a dependency with full type safety and health awareness
        
        Returns:
            The injected dependency instance
        """
        # Resolve service name from type mapping
        if self.dependency_type and self.dependency_type in _service_type_mapping:
            service_name = _service_type_mapping[self.dependency_type]
        elif self.dependency_type and hasattr(self.dependency_type, '__name__'):
            # Fallback to type name
            service_name = self.dependency_type.__name__
        else:
            raise ValueError("Cannot resolve service name for injection")
        
        # Get instance from registry
        instance = _service_registry.get(service_name)
        if instance is None:
            if self.fallback_to:
                logging.warning(f"Service '{service_name}' not registered for injection, using fallback")
                return self.fallback_to
            raise ValueError(f"Service '{service_name}' not registered for injection")
        
        # Check if the instance implements BaseProvider for health awareness
        # Import locally to avoid circular import
        from ...data.storage.providers.base_provider import BaseProvider
        if isinstance(instance, BaseProvider):
            # Perform health check
            is_healthy = await instance.check_health()
            
            # Update health registry
            health_state = {
                "service_name": service_name,
                "is_healthy": is_healthy,
                "last_check": datetime.now(),
                "instance": instance
            }
            self.register_health_state(service_name, health_state)
            
            if not is_healthy:
                # Log critical warning about unhealthy dependency
                logging.warning(f"CRITICAL: Service '{service_name}' is unhealthy. Preparing for degraded mode operations.")
                
                # If we have a fallback, use it
                if self.fallback_to:
                    logging.info(f"Using fallback for '{service_name}' service")
                    return self.fallback_to
                
                # Otherwise, return the unhealthy instance but with a health proxy wrapper
                return HealthProxy(instance, service_name)
        
        return instance
    
    @classmethod
    def from_annotated(cls, annotation) -> Any:
        """
        Create inject instance from Pydantic Annotated type
        
        Args:
            annotation: Pydantic Annotated type
            
        Returns:
            Injected dependency instance
        """
        if hasattr(annotation, '__metadata__'):
            # Extract origin type (the actual type)
            origin_type = annotation.__origin__
            
            # Extract metadata for service name
            metadata = annotation.__metadata__
            if metadata:
                # Look for service name in metadata
                for item in metadata:
                    if isinstance(item, str) and item in _service_registry:
                        instance = _service_registry.get(item)
                        if instance is not None:
                            return instance
            
            # Fallback to type-based resolution
            if origin_type in _service_type_mapping:
                service_name = _service_type_mapping[origin_type]
                instance = _service_registry.get(service_name)
                if instance is not None:
                    return instance
        
        raise ValueError(f"Cannot resolve dependency from annotation: {annotation}")

# Global health-aware inject instance
health_aware_inject = HealthAwareInject()


def inject(dependency_type: type[T], fallback_to: Any = None) -> T:
    """
    Type-safe dependency injection function with health awareness
    
    Args:
        dependency_type: The type of dependency to inject
        fallback_to: Fallback instance to use if the primary dependency is unhealthy
        
    Returns:
        The injected dependency instance
        
    Example:
        db = inject(DatabaseService)
        config = inject(ConfigService)
        db_with_fallback = inject(DatabaseService, fallback_to=memory_db)
    """
    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # If we're in a loop, we need to handle it differently
        # For now, we'll create a new event loop in a separate thread
        import concurrent.futures
        import threading
        
        def run_in_thread():
            return asyncio.run(HealthAwareInject(dependency_type, fallback_to)())
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        injector = HealthAwareInject(dependency_type, fallback_to)
        return asyncio.run(injector())


def inject_from_annotation(annotation) -> Any:
    """
    Inject dependency from Pydantic Annotated type with health awareness
    
    Args:
        annotation: Pydantic Annotated type
        
    Returns:
        The injected dependency instance
        
    Example:
        user_id: Annotated[str, "user-id-service"] = inject_from_annotation(...)
    """
    return HealthAwareInject.from_annotated(annotation)


def get_health_registry() -> dict[str, dict[str, Any]]:
    """
    Get the global health registry containing health states of all services
    
    Returns:
        Dictionary with service names as keys and health states as values
    """
    return _health_registry


def get_service_health(service_name: str) -> dict[str, Any] | None:
    """
    Get the health status of a specific service
    
    Args:
        service_name: Name of the service to check
        
    Returns:
        Health state of the service or None if not found
    """
    return _health_registry.get(service_name)


# Provider override mechanism for testing
_overrides: dict[str, Any] = {}

def override(service_name: str, mock_value: Any):
    """Override a service for testing"""
    _overrides[service_name] = mock_value

def reset_overrides():
    """Reset all overrides"""
    global _overrides
    _overrides.clear()


def inject_with_health_check(dependency_type: type[T], fallback_to: Any = None) -> T:
    """
    Inject dependency with explicit health check
    
    Args:
        dependency_type: The type of dependency to inject
        fallback_to: Fallback instance to use if the primary dependency is unhealthy
        
    Returns:
        The injected dependency instance
    """
    # Check if we're already in an event loop
    try:
        loop = asyncio.get_running_loop()
        # If we're in a loop, we need to handle it differently
        import concurrent.futures
        
        def run_in_thread():
            return asyncio.run(HealthAwareInject(dependency_type, fallback_to)())
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        injector = HealthAwareInject(dependency_type, fallback_to)
        return asyncio.run(injector())

# Convenience aliases for common injection patterns
def inject_db() -> Any:
    """Inject database service"""
    return inject_from_annotation(Annotated[Any, "database"])

def inject_config() -> Any:
    """Inject configuration service"""
    return inject_from_annotation(Annotated[Any, "config"])