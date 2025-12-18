"""
Dependency Injection - Lazy provider-based injection system

Provides lazy resolution of dependencies without eager instantiation.
Supports service proxies, database connections, and configuration.

Rationale:
- Lazy loading: Dependencies are only instantiated when actually needed
- Type safety: Pydantic's Annotated support enables compile-time checking
- Testability: Easy mocking and override mechanisms for unit testing
- Performance: Zero-cost initialization until first access
"""
from typing import Optional, Type, TypeVar, Generic, get_type_hints
from functools import wraps
from pydantic import BaseModel
try:
    from typing import Annotated
except ImportError:
    # For Python < 3.9, use typing_extensions
    from typing_extensions import Annotated


T = TypeVar('T')

class Inject(Generic[T]):
    """
    Lazy provider-based dependency injection system with type safety
    
    Provides lazy resolution of dependencies without eager instantiation.
    Supports Pydantic's Annotated for type-safe injection.
    """
    
    def __class_getitem__(cls, item):
        """Support for generic type annotation"""
        return cls(item)
    
    def __init__(self, dependency_type: Type[T] = None):
        self.dependency_type = dependency_type
    
    def __call__(self, dependency_identifier: str = None):
        """
        Inject a dependency lazily with zero-cost initialization
        
        Args:
            dependency_identifier: Identifier for the dependency to inject
            
        Returns:
            Lazy dependency resolver
        """
        if self.dependency_type and hasattr(self.dependency_type, '__name__'):
            # Use type name as identifier if not provided
            dependency_identifier = dependency_identifier or self.dependency_type.__name__
        
        # Handle different dependency types
        if dependency_identifier == 'service':
            return self._inject_service()
        elif dependency_identifier == 'db' or dependency_identifier == 'database':
            return self._inject_database()
        elif dependency_identifier == 'config':
            return self._inject_config()
        else:
            return self._inject_generic(dependency_identifier)
    
    @classmethod
    def from_annotation(cls, annotation):
        """
        Create inject instance from Pydantic Annotated type
        
        Args:
            annotation: Pydantic Annotated type
            
        Returns:
            Inject instance configured from annotation
        """
        if hasattr(annotation, '__metadata__'):
            # This is an Annotated type
            metadata = annotation.__metadata__
            if metadata and len(metadata) > 0:
                # Extract dependency identifier from metadata
                dep_id = metadata[0] if isinstance(metadata[0], str) else None
                return cls(annotation.__origin__)(dep_id)
        
        # Fallback to regular type injection
        return cls(annotation)()
    
    def _inject_service(self):
        """Inject a service proxy lazily"""
        from evox.core.proxy import ServiceProxy
        
        class LazyServiceProxy:
            def __init__(self, service_name=None):
                self.service_name = service_name
                self._proxy = None
            
            def __getattr__(self, method_name):
                # Check for override first
                override_key = f"service:{self.service_name}" if self.service_name else "service"
                if override_key in _overrides:
                    return getattr(_overrides[override_key], method_name)
                
                # Zero-cost until first resolution
                if self._proxy is None:
                    self._proxy = ServiceProxy.get_instance(self.service_name or "default")
                return getattr(self._proxy, method_name)
            
            def __call__(self, *args, **kwargs):
                # Check for override first
                override_key = f"service:{self.service_name}" if self.service_name else "service"
                if override_key in _overrides:
                    return _overrides[override_key](*args, **kwargs)
                
                # Zero-cost until first resolution
                if self._proxy is None:
                    self._proxy = ServiceProxy.get_instance(self.service_name or "default")
                return self._proxy(*args, **kwargs)
        
        return LazyServiceProxy()
    
    def _inject_database(self):
        """Inject database connection lazily"""
        from evox.core.storage import data_io
        
        class LazyDBProxy:
            def __init__(self):
                self._initialized = False
            
            def __getattr__(self, attr):
                # Check for override first
                if 'db' in _overrides:
                    return getattr(_overrides['db'], attr)
                
                # Lazy initialization on first access
                if not self._initialized:
                    # In a real implementation, this would initialize the DB connection
                    self._initialized = True
                # Delegate to data_io for actual operations
                return getattr(data_io, attr)
        
        return LazyDBProxy()
    
    def _inject_config(self, section: Optional[str] = None):
        """Inject configuration lazily"""
        from evox.core.config import get_config as _get_config
        
        class LazyConfigProxy:
            def __init__(self, section=None):
                self.section = section
                self._cache = {}
            
            def __getattr__(self, key):
                # Check for override first
                override_key = f"config:{self.section}" if self.section else "config"
                if override_key in _overrides:
                    config_override = _overrides[override_key]
                    return getattr(config_override, key) if hasattr(config_override, key) else config_override.get(key)
                
                # Return configuration value lazily
                cache_key = f"{self.section}.{key}" if self.section else key
                if cache_key not in self._cache:
                    self._cache[cache_key] = _get_config(cache_key)
                return self._cache[cache_key]
            
            def get(self, key: str, default=None):
                """Get configuration value with default"""
                # Check for override first
                override_key = f"config:{self.section}" if self.section else "config"
                if override_key in _overrides:
                    config_override = _overrides[override_key]
                    return config_override.get(key, default) if hasattr(config_override, 'get') else getattr(config_override, key, default)
                
                cache_key = f"{self.section}.{key}" if self.section else key
                if cache_key not in self._cache:
                    self._cache[cache_key] = _get_config(cache_key, default)
                return self._cache[cache_key]
        
        return LazyConfigProxy(section)
    
    def _inject_generic(self, identifier: str):
        """Inject a generic dependency"""
        class LazyGenericProxy:
            def __init__(self, identifier):
                self.identifier = identifier
                self._instance = None
            
            def __getattr__(self, attr):
                # Check for override first
                if self.identifier in _overrides:
                    return getattr(_overrides[self.identifier], attr)
                
                # Lazy resolution
                if self._instance is None:
                    # Try to resolve from service instances
                    from evox.core.service_builder import ServiceBuilder
                    self._instance = ServiceBuilder.get_instance(self.identifier)
                    if self._instance is None:
                        # Fall back to simple resolution
                        self._instance = self._resolve_dependency()
                return getattr(self._instance, attr)
            
            def _resolve_dependency(self):
                """Resolve dependency based on identifier"""
                # This is a simplified resolution - in a real implementation,
                # this would use a more sophisticated dependency resolution mechanism
                return object()
        
        return LazyGenericProxy(identifier)
    
    @staticmethod
    def db():
        """
        Inject database connection lazily
        
        Returns:
            Lazy database proxy resolver
        """
        # Return a lazy database proxy that resolves at call time
        from evox.core.storage import data_io
        
        class LazyDBProxy:
            def __init__(self):
                self._initialized = False
            
            def __getattr__(self, attr):
                # Check for override first
                if 'db' in _overrides:
                    return getattr(_overrides['db'], attr)
                
                # Lazy initialization on first access
                if not self._initialized:
                    # In a real implementation, this would initialize the DB connection
                    self._initialized = True
                # Delegate to data_io for actual operations
                return getattr(data_io, attr)
        
        return LazyDBProxy()
    
    @staticmethod
    def config(section: Optional[str] = None):
        """
        Inject configuration lazily
        
        Args:
            section: Configuration section to inject
            
        Returns:
            Lazy configuration resolver
        """
        from evox.core.config import get_config as _get_config
        
        class LazyConfigProxy:
            def __init__(self, section=None):
                self.section = section
                self._cache = {}
            
            def __getattr__(self, key):
                # Check for override first
                override_key = f"config:{self.section}" if self.section else "config"
                if override_key in _overrides:
                    config_override = _overrides[override_key]
                    return getattr(config_override, key) if hasattr(config_override, key) else config_override.get(key)
                
                # Return configuration value lazily
                cache_key = f"{self.section}.{key}" if self.section else key
                if cache_key not in self._cache:
                    self._cache[cache_key] = _get_config(cache_key)
                return self._cache[cache_key]
            
            def get(self, key: str, default=None):
                """Get configuration value with default"""
                # Check for override first
                override_key = f"config:{self.section}" if self.section else "config"
                if override_key in _overrides:
                    config_override = _overrides[override_key]
                    return config_override.get(key, default) if hasattr(config_override, 'get') else getattr(config_override, key, default)
                
                cache_key = f"{self.section}.{key}" if self.section else key
                if cache_key not in self._cache:
                    self._cache[cache_key] = _get_config(cache_key, default)
                return self._cache[cache_key]
        
        return LazyConfigProxy(section)


# Global inject instance factory
inject = Inject()

# Enhanced inject function that supports both string identifiers and type annotations
class EnhancedInject:
    """Enhanced inject function that supports both string identifiers and type annotations
    
    Rationale:
        Unified interface that supports both legacy string-based injection
        and modern type-annotated injection for gradual migration.
    """
    
    def __call__(self, dependency_identifier=None):
        """Inject dependency by identifier or type"""
        if dependency_identifier is None:
            return Inject()
        elif isinstance(dependency_identifier, str):
            # String identifier
            return Inject()(dependency_identifier)
        else:
            # Type annotation
            return inject_dependency(dependency_identifier)
    
    def __getattr__(self, name):
        """Support for direct attribute access like inject.db, inject.config"""
        if name in ['db', 'config', 'service']:
            return getattr(Inject(), name)()
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

# Replace global inject with enhanced version
inject = EnhancedInject()

# Convenience function for type-safe injection
def inject_dependency(dependency_type: Type[T]) -> T:
    """Convenience function for type-safe dependency injection"""
    # Check if this is an Annotated type
    if hasattr(dependency_type, '__metadata__'):
        return Inject.from_annotation(dependency_type)
    return Inject(dependency_type)()


# Provider override mechanism for testing
_overrides = {}

def override(provider, mock_value):
    """Override a provider for testing"""
    _overrides[provider] = mock_value

def reset_overrides():
    """Reset all overrides"""
    global _overrides
    _overrides.clear()