"""
Base Provider for Enterprise System
==================================

This module defines the base provider pattern used throughout the enterprise system.
Providers implement the BaseProvider interface and can be registered with the
ServiceRegistry for service-to-service communication and dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar
from evox.core.registry import get_service_registry
from evox.core.inject import HealthAwareInject
from evox.core.data_io import data_io


T = TypeVar('T')


class BaseProvider(ABC):
    """
    Base Provider Interface for Enterprise System
    
    All enterprise providers should inherit from this base class to ensure
    consistent behavior across the system. Providers handle specific business
    logic or infrastructure concerns and are managed by the ServiceRegistry.
    """
    
    def __init__(self, name: str):
        """
        Initialize the provider with a name.
        
        Args:
            name: The unique name of this provider instance
        """
        self._name = name
        self._initialized = False
        self._healthy = True
        self._health_details: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        """Get the provider name."""
        return self._name
    
    @property
    def initialized(self) -> bool:
        """Check if the provider has been initialized."""
        return self._initialized
    
    @property
    def healthy(self) -> bool:
        """Check if the provider is healthy."""
        return self._healthy
    
    @property
    def health_details(self) -> Dict[str, Any]:
        """Get detailed health information."""
        return self._health_details.copy()
    
    async def initialize(self) -> bool:
        """
        Initialize the provider.
        
        This method is called when the provider is first loaded. Override this
        method to perform any necessary setup operations.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            await self._setup()
            self._initialized = True
            self._healthy = True
            return True
        except Exception as e:
            self._healthy = False
            self._health_details = {"error": str(e), "status": "initialization_failed"}
            return False
    
    async def _setup(self):
        """
        Internal setup method. Override this in subclasses.
        
        This method should contain the actual initialization logic for the provider.
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the provider.
        
        Returns:
            Dictionary containing health status and details
        """
        try:
            # Perform the actual health check
            result = await self._perform_health_check()
            
            self._healthy = result.get("healthy", True)
            self._health_details = result
            
            return {
                "name": self._name,
                "healthy": self._healthy,
                "timestamp": result.get("timestamp", "unknown"),
                "details": result
            }
        except Exception as e:
            self._healthy = False
            self._health_details = {"error": str(e), "status": "health_check_failed"}
            return {
                "name": self._name,
                "healthy": False,
                "error": str(e),
                "details": self._health_details
            }
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """
        Internal health check method. Override this in subclasses.
        
        This method should contain the actual health check logic for the provider.
        """
        return {
            "status": "ok",
            "timestamp": "2024-01-01T00:00:00Z",  # In real app, use current timestamp
            "healthy": True
        }
    
    async def close(self):
        """
        Close the provider and release any resources.
        
        Override this method to perform cleanup operations when the provider
        is being shut down.
        """
        pass


class DataProvider(BaseProvider):
    """
    Base Data Provider for Enterprise System
    
    This provider handles data storage and retrieval with intent-aware behavior.
    It implements the multi-layered caching system with automatic fallback.
    """
    
    def __init__(self, name: str, namespace: str):
        """
        Initialize the data provider.
        
        Args:
            name: The unique name of this provider instance
            namespace: The data namespace to use for storage
        """
        super().__init__(name)
        self._namespace = namespace
    
    async def _setup(self):
        """Setup the data provider."""
        # Initialize the data IO for this namespace
        await data_io.namespace(self._namespace).initialize()
    
    async def get(self, key: str, fallback: str = "normal") -> Any | None:
        """
        Get a value from the multi-layered cache system.
        
        Args:
            key: The key to retrieve
            fallback: Fallback strategy ("normal", "aggressive", "registry")
            
        Returns:
            The value if found, None otherwise
        """
        return await data_io.namespace(self._namespace).read(key, fallback=fallback)
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in the multi-layered cache system.
        
        Args:
            key: The key to store
            value: The value to store
            ttl: Time-to-live in seconds (None for no expiration)
        """
        await data_io.namespace(self._namespace).write(key, value, ttl=ttl)
    
    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache system.
        
        Args:
            key: The key to delete
        """
        await data_io.namespace(self._namespace).delete(key)
    
    async def keys(self, pattern: str) -> list[str]:
        """
        Get keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports wildcards)
            
        Returns:
            List of matching keys
        """
        return await data_io.namespace(self._namespace).keys(pattern)


class CommunicationProvider(BaseProvider):
    """
    Service-to-Service Communication Provider
    
    This provider handles communication between services in the enterprise system.
    It uses the ServiceRegistry to discover and communicate with other services.
    """
    
    def __init__(self, name: str, service_registry = None):
        """
        Initialize the communication provider.
        
        Args:
            name: The unique name of this provider instance
            service_registry: Optional service registry instance
        """
        super().__init__(name)
        self._registry = service_registry or get_service_registry()
        self._initialized_services = set()
    
    async def _setup(self):
        """Setup the communication provider."""
        # Register this provider with the registry
        await self._registry.register_service(
            self._name,
            service_type="communication",
            metadata={"provider": True}
        )
    
    async def call_service(self, service_name: str, method: str, **kwargs) -> Any | None:
        """
        Call a method on another service.
        
        Args:
            service_name: Name of the target service
            method: Method to call on the target service
            **kwargs: Arguments to pass to the method
            
        Returns:
            Result of the method call, or None if failed
        """
        try:
            # Check if the target service is available
            service_info = self._registry.get_service(service_name)
            if not service_info:
                raise Exception(f"Service {service_name} not found in registry")
            
            # Check service health before calling
            health_info = await self._registry.get_service_health(service_name)
            if not health_info.get("is_healthy", False):
                print(f"Warning: Service {service_name} is unhealthy, using fallback")
                return None
            
            # In a real implementation, this would make the actual service call
            # For this example, we'll simulate the call
            result = await self._simulate_service_call(service_name, method, **kwargs)
            return result
            
        except Exception as e:
            print(f"Error calling service {service_name}.{method}: {e}")
            # Try fallback mechanism
            return await self._try_fallback_call(service_name, method, **kwargs)
    
    async def _simulate_service_call(self, service_name: str, method: str, **kwargs) -> Any:
        """
        Simulate a service call (in real implementation, this would make actual network calls).
        """
        # This is where the actual service communication would happen
        # For this example, we'll return a simulated response
        return {
            "service": service_name,
            "method": method,
            "args": kwargs,
            "result": f"Simulated call to {service_name}.{method}",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    async def _try_fallback_call(self, service_name: str, method: str, **kwargs) -> Any | None:
        """
        Try to call the service using fallback mechanisms.
        """
        # In a real implementation, this would try alternative communication paths
        # or return cached results
        print(f"Using fallback for service {service_name}.{method}")
        return None
    
    async def broadcast_to_services(self, service_type: str, method: str, **kwargs) -> Dict[str, Any]:
        """
        Broadcast a call to all services of a specific type.
        
        Args:
            service_type: Type of services to call
            method: Method to call on matching services
            **kwargs: Arguments to pass to the method
            
        Returns:
            Dictionary mapping service names to their results
        """
        results = {}
        
        # Get all services of the specified type
        services = self._registry.get_services_by_capability(service_type)
        
        for service_info in services:
            try:
                result = await self.call_service(service_info.name, method, **kwargs)
                results[service_info.name] = result
            except Exception as e:
                results[service_info.name] = {"error": str(e)}
        
        return results